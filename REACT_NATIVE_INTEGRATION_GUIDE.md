# React Native Mobile App Integration Guide

## 📋 Table of Contents

1. [Setup & Installation](#setup--installation)
2. [API Client Configuration](#api-client-configuration)
3. [Authentication](#authentication)
4. [API Endpoints Reference](#api-endpoints-reference)
5. [Data Models](#data-models)
6. [Example Implementations](#example-implementations)
7. [State Management](#state-management)
8. [Error Handling](#error-handling)
9. [Best Practices](#best-practices)

---

## 🚀 Setup & Installation

### 1. Install Required Dependencies

```bash
npm install axios @react-native-async-storage/async-storage
# or
yarn add axios @react-native-async-storage/async-storage
```

### 2. Install Additional Utilities (Optional but Recommended)

```bash
npm install react-query @tanstack/react-query
# or
yarn add react-query @tanstack/react-query
```

---

## 🔧 API Client Configuration

### Create API Client (`src/services/api.ts`)

```typescript
import axios, { AxiosInstance, AxiosError } from 'axios';
import AsyncStorage from '@react-native-async-storage/async-storage';

// Update with your backend URL
const BASE_URL = __DEV__ 
  ? 'http://localhost:8000'  // Development
  : 'https://your-backend-url.com';  // Production

class ApiClient {
  private client: AxiosInstance;

  constructor() {
    this.client = axios.create({
      baseURL: BASE_URL,
      timeout: 30000,
      headers: {
        'Content-Type': 'application/json',
      },
    });

    // Request interceptor to add auth token
    this.client.interceptors.request.use(
      async (config) => {
        const token = await AsyncStorage.getItem('accessToken');
        if (token) {
          config.headers.Authorization = `Bearer ${token}`;
        }
        return config;
      },
      (error) => Promise.reject(error)
    );

    // Response interceptor for error handling
    this.client.interceptors.response.use(
      (response) => response,
      async (error: AxiosError) => {
        if (error.response?.status === 401) {
          // Token expired, try to refresh
          const refreshed = await this.refreshToken();
          if (refreshed) {
            // Retry original request
            const originalRequest = error.config;
            if (originalRequest) {
              const token = await AsyncStorage.getItem('accessToken');
              if (token && originalRequest.headers) {
                originalRequest.headers.Authorization = `Bearer ${token}`;
              }
              return this.client(originalRequest);
            }
          } else {
            // Refresh failed, logout user
            await this.logout();
          }
        }
        return Promise.reject(error);
      }
    );
  }

  private async refreshToken(): Promise<boolean> {
    try {
      const refreshToken = await AsyncStorage.getItem('refreshToken');
      if (!refreshToken) return false;

      const response = await axios.post(`${BASE_URL}/api/v1/auth/refresh-token`, {
        refreshToken,
      });

      if (response.data.success) {
        await AsyncStorage.setItem('accessToken', response.data.data.token);
        await AsyncStorage.setItem('refreshToken', response.data.data.refreshToken);
        return true;
      }
      return false;
    } catch (error) {
      return false;
    }
  }

  private async logout() {
    await AsyncStorage.multiRemove(['accessToken', 'refreshToken', 'user']);
    // Navigate to login screen
    // navigationRef.navigate('Login');
  }

  // Generic request methods
  async get<T>(url: string, params?: any): Promise<T> {
    const response = await this.client.get(url, { params });
    return response.data;
  }

  async post<T>(url: string, data?: any): Promise<T> {
    const response = await this.client.post(url, data);
    return response.data;
  }

  async put<T>(url: string, data?: any): Promise<T> {
    const response = await this.client.put(url, data);
    return response.data;
  }

  async delete<T>(url: string): Promise<T> {
    const response = await this.client.delete(url);
    return response.data;
  }
}

export const apiClient = new ApiClient();
```

---

## 🔐 Authentication

### Auth Service (`src/services/authService.ts`)

```typescript
import { apiClient } from './api';
import AsyncStorage from '@react-native-async-storage/async-storage';

export interface LoginCredentials {
  email: string;
  password: string;
}

export interface RegisterData {
  name: string;
  email: string;
  phone: string;
  password: string;
  confirm_password: string;
  business_name: string;
  gst_number?: string;
  address?: any;
}

export interface User {
  id: string;
  name: string;
  email: string;
  phone: string;
  business_name: string;
  gst_number?: string;
  kyc_status: 'pending' | 'verified' | 'rejected';
  is_active: boolean;
}

export interface AuthResponse {
  success: boolean;
  data: {
    token: string;
    refreshToken: string;
    user: User;
  };
  message: string;
}

class AuthService {
  async login(credentials: LoginCredentials): Promise<AuthResponse> {
    const response = await apiClient.post<AuthResponse>(
      '/api/v1/auth/login',
      credentials
    );

    if (response.success) {
      await AsyncStorage.setItem('accessToken', response.data.token);
      await AsyncStorage.setItem('refreshToken', response.data.refreshToken);
      await AsyncStorage.setItem('user', JSON.stringify(response.data.user));
    }

    return response;
  }

  async register(data: RegisterData): Promise<AuthResponse> {
    const response = await apiClient.post<AuthResponse>(
      '/api/v1/auth/register',
      data
    );

    if (response.success) {
      await AsyncStorage.setItem('accessToken', response.data.token);
      await AsyncStorage.setItem('refreshToken', response.data.refreshToken);
      await AsyncStorage.setItem('user', JSON.stringify(response.data.user));
    }

    return response;
  }

  async logout(): Promise<void> {
    try {
      await apiClient.post('/api/v1/auth/logout');
    } catch (error) {
      console.error('Logout error:', error);
    } finally {
      await AsyncStorage.multiRemove(['accessToken', 'refreshToken', 'user']);
    }
  }

  async getCurrentUser(): Promise<User | null> {
    try {
      const userStr = await AsyncStorage.getItem('user');
      return userStr ? JSON.parse(userStr) : null;
    } catch (error) {
      return null;
    }
  }

  async isAuthenticated(): Promise<boolean> {
    const token = await AsyncStorage.getItem('accessToken');
    return !!token;
  }
}

export const authService = new AuthService();
```

---

## 📡 API Endpoints Reference

### Products API (`src/services/productService.ts`)

```typescript
import { apiClient } from './api';

export interface Product {
  id: string;
  name: string;
  slug: string;
  description?: string;
  brand?: {
    id: string;
    name: string;
    logoUrl?: string;
  };
  company?: {
    id: string;
    name: string;
    logoUrl?: string;
  };
  category?: {
    id: string;
    name: string;
    slug: string;
  };
  mrp: number;
  sellingPrice: number;
  discount: number;
  stockQuantity: number;
  minOrderQuantity: number;
  unit: string;
  piecesPerSet: number;
  specifications?: Record<string, any>;
  isFeatured: boolean;
  isAvailable: boolean;
  images: Array<{
    url: string;
    isPrimary: boolean;
  }>;
  rating: number;
  reviewCount: number;
  createdAt: string;
}

export interface ProductListParams {
  page?: number;
  limit?: number;
  category?: string;
  company?: string;
  brand?: string;
  search?: string;
  minPrice?: number;
  maxPrice?: number;
  sort?: 'price_asc' | 'price_desc' | 'name' | 'popularity' | 'created_at';
  featured?: boolean;
}

export interface ProductListResponse {
  success: boolean;
  data: {
    products: Product[];
    pagination: {
      page: number;
      limit: number;
      total: number;
      totalPages: number;
    };
  };
}

class ProductService {
  async getProducts(params?: ProductListParams): Promise<ProductListResponse> {
    return apiClient.get<ProductListResponse>('/api/v1/products', params);
  }

  async getProductById(id: string): Promise<{ success: boolean; data: Product }> {
    return apiClient.get<{ success: boolean; data: Product }>(`/api/v1/products/${id}`);
  }

  async getProductBySlug(slug: string): Promise<{ success: boolean; data: Product }> {
    return apiClient.get<{ success: boolean; data: Product }>(`/api/v1/products/slug/${slug}`);
  }

  async getFeaturedProducts(limit: number = 6): Promise<{ success: boolean; data: Product[] }> {
    return apiClient.get<{ success: boolean; data: Product[] }>('/api/v1/products/featured', { limit });
  }

  async searchProducts(query: string, params?: ProductListParams): Promise<ProductListResponse> {
    return apiClient.get<ProductListResponse>('/api/v1/products/search', {
      q: query,
      ...params,
    });
  }
}

export const productService = new ProductService();
```

### Categories API (`src/services/categoryService.ts`)

```typescript
import { apiClient } from './api';

export interface Category {
  id: string;
  name: string;
  slug: string;
  icon?: string;
  color?: string;
  imageUrl?: string;
  productCount: number;
  children?: Category[];
}

class CategoryService {
  async getCategories(): Promise<{ success: boolean; data: Category[] }> {
    return apiClient.get<{ success: boolean; data: Category[] }>('/api/v1/categories');
  }

  async getCategoryProducts(
    categoryId: string,
    page: number = 1,
    limit: number = 20
  ): Promise<any> {
    return apiClient.get(`/api/v1/categories/${categoryId}/products`, {
      page,
      limit,
    });
  }
}

export const categoryService = new CategoryService();
```

### Offers API (`src/services/offerService.ts`)

```typescript
import { apiClient } from './api';

export interface Offer {
  id: string;
  title: string;
  description?: string;
  imageUrl?: string;
  validFrom: string;
  validTo: string;
  company?: {
    id: string;
    name: string;
  };
}

export interface OffersResponse {
  success: boolean;
  data: {
    banners: Offer[];
    textOffers: Offer[];
    companyOffers: Offer[];
  };
}

class OfferService {
  async getOffers(): Promise<OffersResponse> {
    return apiClient.get<OffersResponse>('/api/v1/offers');
  }
}

export const offerService = new OfferService();
```

### Cart API (`src/services/cartService.ts`)

```typescript
import { apiClient } from './api';

export interface CartItem {
  id: string;
  product: {
    id: string;
    name: string;
    imageUrl?: string;
    sellingPrice: number;
  };
  quantity: number;
  subtotal: number;
}

export interface Cart {
  id: string;
  items: CartItem[];
  total: number;
}

class CartService {
  async getCart(): Promise<{ success: boolean; data: Cart }> {
    return apiClient.get<{ success: boolean; data: Cart }>('/api/v1/cart');
  }

  async addToCart(productId: string, quantity: number): Promise<any> {
    return apiClient.post('/api/v1/cart/add', {
      product_id: productId,
      quantity,
    });
  }

  async updateCartItem(itemId: string, quantity: number): Promise<any> {
    return apiClient.put(`/api/v1/cart/items/${itemId}`, { quantity });
  }

  async removeFromCart(itemId: string): Promise<any> {
    return apiClient.delete(`/api/v1/cart/items/${itemId}`);
  }

  async clearCart(): Promise<any> {
    return apiClient.delete('/api/v1/cart');
  }
}

export const cartService = new CartService();
```

### Orders API (`src/services/orderService.ts`)

```typescript
import { apiClient } from './api';

export interface OrderItem {
  id: string;
  product: {
    id: string;
    name: string;
    imageUrl?: string;
  };
  quantity: number;
  unitPrice: number;
  subtotal: number;
}

export interface Order {
  id: string;
  order_number: string;
  status: 'pending' | 'confirmed' | 'processing' | 'shipped' | 'delivered' | 'cancelled';
  items: OrderItem[];
  subtotal: number;
  discount: number;
  delivery_charge: number;
  tax: number;
  total: number;
  delivery_address: any;
  payment_method: string;
  payment_status: string;
  created_at: string;
}

class OrderService {
  async createOrder(orderData: {
    items: Array<{ product_id: string; quantity: number }>;
    delivery_address: any;
    payment_method: string;
  }): Promise<{ success: boolean; data: Order }> {
    return apiClient.post<{ success: boolean; data: Order }>('/api/v1/orders', orderData);
  }

  async getOrders(): Promise<{ success: boolean; data: { orders: Order[] } }> {
    return apiClient.get<{ success: boolean; data: { orders: Order[] } }>('/api/v1/orders');
  }

  async getOrderById(orderId: string): Promise<{ success: boolean; data: Order }> {
    return apiClient.get<{ success: boolean; data: Order }>(`/api/v1/orders/${orderId}`);
  }
}

export const orderService = new OrderService();
```

---

## 💡 Example Implementations

### 1. Product List Screen (`src/screens/ProductListScreen.tsx`)

```typescript
import React, { useState, useEffect } from 'react';
import {
  View,
  FlatList,
  Text,
  Image,
  TouchableOpacity,
  ActivityIndicator,
  StyleSheet,
} from 'react-native';
import { productService, Product } from '../services/productService';

export const ProductListScreen: React.FC = () => {
  const [products, setProducts] = useState<Product[]>([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [hasMore, setHasMore] = useState(true);

  useEffect(() => {
    loadProducts();
  }, []);

  const loadProducts = async (pageNum: number = 1) => {
    try {
      setLoading(true);
      const response = await productService.getProducts({
        page: pageNum,
        limit: 20,
        sort: 'popularity',
      });

      if (response.success) {
        if (pageNum === 1) {
          setProducts(response.data.products);
        } else {
          setProducts((prev) => [...prev, ...response.data.products]);
        }

        setHasMore(pageNum < response.data.pagination.totalPages);
      }
    } catch (error) {
      console.error('Error loading products:', error);
    } finally {
      setLoading(false);
    }
  };

  const loadMore = () => {
    if (!loading && hasMore) {
      const nextPage = page + 1;
      setPage(nextPage);
      loadProducts(nextPage);
    }
  };

  const renderProduct = ({ item }: { item: Product }) => {
    const primaryImage = item.images.find((img) => img.isPrimary) || item.images[0];

    return (
      <TouchableOpacity style={styles.productCard}>
        <Image
          source={{ uri: primaryImage?.url }}
          style={styles.productImage}
          resizeMode="cover"
        />
        <View style={styles.productInfo}>
          <Text style={styles.productName}>{item.name}</Text>
          {item.brand && (
            <Text style={styles.brandName}>{item.brand.name}</Text>
          )}
          <View style={styles.priceContainer}>
            <Text style={styles.sellingPrice}>₹{item.sellingPrice}</Text>
            {item.discount > 0 && (
              <>
                <Text style={styles.mrp}>₹{item.mrp}</Text>
                <Text style={styles.discount}>{item.discount}% OFF</Text>
              </>
            )}
          </View>
          <Text style={styles.stock}>
            {item.stockQuantity > 0
              ? `In Stock (${item.stockQuantity})`
              : 'Out of Stock'}
          </Text>
        </View>
      </TouchableOpacity>
    );
  };

  if (loading && products.length === 0) {
    return (
      <View style={styles.center}>
        <ActivityIndicator size="large" />
      </View>
    );
  }

  return (
    <FlatList
      data={products}
      renderItem={renderProduct}
      keyExtractor={(item) => item.id}
      onEndReached={loadMore}
      onEndReachedThreshold={0.5}
      ListFooterComponent={
        loading && products.length > 0 ? (
          <ActivityIndicator size="small" />
        ) : null
      }
    />
  );
};

const styles = StyleSheet.create({
  center: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  productCard: {
    flexDirection: 'row',
    padding: 12,
    borderBottomWidth: 1,
    borderBottomColor: '#eee',
  },
  productImage: {
    width: 100,
    height: 100,
    borderRadius: 8,
    marginRight: 12,
  },
  productInfo: {
    flex: 1,
  },
  productName: {
    fontSize: 16,
    fontWeight: '600',
    marginBottom: 4,
  },
  brandName: {
    fontSize: 14,
    color: '#666',
    marginBottom: 8,
  },
  priceContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 4,
  },
  sellingPrice: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#000',
    marginRight: 8,
  },
  mrp: {
    fontSize: 14,
    color: '#999',
    textDecorationLine: 'line-through',
    marginRight: 8,
  },
  discount: {
    fontSize: 12,
    color: '#e74c3c',
    fontWeight: '600',
  },
  stock: {
    fontSize: 12,
    color: '#27ae60',
  },
});
```

### 2. Product Detail Screen (`src/screens/ProductDetailScreen.tsx`)

```typescript
import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  Image,
  ScrollView,
  TouchableOpacity,
  StyleSheet,
  ActivityIndicator,
} from 'react-native';
import { productService, Product } from '../services/productService';
import { cartService } from '../services/cartService';

export const ProductDetailScreen: React.FC<{ route: any }> = ({ route }) => {
  const { productId } = route.params;
  const [product, setProduct] = useState<Product | null>(null);
  const [loading, setLoading] = useState(true);
  const [quantity, setQuantity] = useState(1);

  useEffect(() => {
    loadProduct();
  }, [productId]);

  const loadProduct = async () => {
    try {
      setLoading(true);
      const response = await productService.getProductById(productId);
      if (response.success) {
        setProduct(response.data);
      }
    } catch (error) {
      console.error('Error loading product:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleAddToCart = async () => {
    if (!product) return;

    try {
      await cartService.addToCart(product.id, quantity);
      // Show success message
      alert('Product added to cart!');
    } catch (error) {
      console.error('Error adding to cart:', error);
      alert('Failed to add product to cart');
    }
  };

  if (loading) {
    return (
      <View style={styles.center}>
        <ActivityIndicator size="large" />
      </View>
    );
  }

  if (!product) {
    return (
      <View style={styles.center}>
        <Text>Product not found</Text>
      </View>
    );
  }

  const primaryImage = product.images.find((img) => img.isPrimary) || product.images[0];

  return (
    <ScrollView style={styles.container}>
      <Image
        source={{ uri: primaryImage?.url }}
        style={styles.mainImage}
        resizeMode="cover"
      />

      <View style={styles.content}>
        <Text style={styles.productName}>{product.name}</Text>

        {product.brand && (
          <Text style={styles.brandName}>{product.brand.name}</Text>
        )}

        <View style={styles.priceContainer}>
          <Text style={styles.sellingPrice}>₹{product.sellingPrice}</Text>
          {product.discount > 0 && (
            <>
              <Text style={styles.mrp}>₹{product.mrp}</Text>
              <Text style={styles.discount}>{product.discount}% OFF</Text>
            </>
          )}
        </View>

        {product.description && (
          <Text style={styles.description}>{product.description}</Text>
        )}

        {product.specifications && (
          <View style={styles.specsContainer}>
            <Text style={styles.specsTitle}>Specifications</Text>
            {Object.entries(product.specifications).map(([key, value]) => (
              <View key={key} style={styles.specRow}>
                <Text style={styles.specKey}>{key}:</Text>
                <Text style={styles.specValue}>{String(value)}</Text>
              </View>
            ))}
          </View>
        )}

        <View style={styles.quantityContainer}>
          <Text style={styles.quantityLabel}>Quantity:</Text>
          <View style={styles.quantityControls}>
            <TouchableOpacity
              onPress={() => setQuantity(Math.max(1, quantity - 1))}
              style={styles.quantityButton}
            >
              <Text>-</Text>
            </TouchableOpacity>
            <Text style={styles.quantityValue}>{quantity}</Text>
            <TouchableOpacity
              onPress={() => setQuantity(quantity + 1)}
              style={styles.quantityButton}
            >
              <Text>+</Text>
            </TouchableOpacity>
          </View>
        </View>

        <TouchableOpacity
          style={styles.addToCartButton}
          onPress={handleAddToCart}
          disabled={product.stockQuantity === 0}
        >
          <Text style={styles.addToCartText}>
            {product.stockQuantity > 0 ? 'Add to Cart' : 'Out of Stock'}
          </Text>
        </TouchableOpacity>
      </View>
    </ScrollView>
  );
};

const styles = StyleSheet.create({
  center: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  container: {
    flex: 1,
    backgroundColor: '#fff',
  },
  mainImage: {
    width: '100%',
    height: 300,
  },
  content: {
    padding: 16,
  },
  productName: {
    fontSize: 24,
    fontWeight: 'bold',
    marginBottom: 8,
  },
  brandName: {
    fontSize: 16,
    color: '#666',
    marginBottom: 12,
  },
  priceContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 16,
  },
  sellingPrice: {
    fontSize: 28,
    fontWeight: 'bold',
    color: '#000',
    marginRight: 12,
  },
  mrp: {
    fontSize: 18,
    color: '#999',
    textDecorationLine: 'line-through',
    marginRight: 12,
  },
  discount: {
    fontSize: 16,
    color: '#e74c3c',
    fontWeight: '600',
  },
  description: {
    fontSize: 16,
    lineHeight: 24,
    marginBottom: 16,
    color: '#333',
  },
  specsContainer: {
    marginBottom: 16,
  },
  specsTitle: {
    fontSize: 18,
    fontWeight: '600',
    marginBottom: 8,
  },
  specRow: {
    flexDirection: 'row',
    paddingVertical: 4,
  },
  specKey: {
    fontSize: 14,
    fontWeight: '600',
    width: 120,
  },
  specValue: {
    fontSize: 14,
    flex: 1,
  },
  quantityContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 16,
  },
  quantityLabel: {
    fontSize: 16,
    marginRight: 12,
  },
  quantityControls: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  quantityButton: {
    width: 40,
    height: 40,
    justifyContent: 'center',
    alignItems: 'center',
    borderWidth: 1,
    borderColor: '#ddd',
    borderRadius: 4,
  },
  quantityValue: {
    fontSize: 18,
    marginHorizontal: 16,
    minWidth: 30,
    textAlign: 'center',
  },
  addToCartButton: {
    backgroundColor: '#3498db',
    padding: 16,
    borderRadius: 8,
    alignItems: 'center',
  },
  addToCartText: {
    color: '#fff',
    fontSize: 18,
    fontWeight: '600',
  },
});
```

### 3. Using React Query for Data Fetching

```typescript
// src/hooks/useProducts.ts
import { useQuery, useInfiniteQuery } from '@tanstack/react-query';
import { productService, ProductListParams } from '../services/productService';

export const useProducts = (params?: ProductListParams) => {
  return useInfiniteQuery({
    queryKey: ['products', params],
    queryFn: ({ pageParam = 1 }) =>
      productService.getProducts({ ...params, page: pageParam }),
    getNextPageParam: (lastPage) => {
      const { pagination } = lastPage.data;
      return pagination.page < pagination.totalPages
        ? pagination.page + 1
        : undefined;
    },
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
};

export const useProduct = (productId: string) => {
  return useQuery({
    queryKey: ['product', productId],
    queryFn: () => productService.getProductById(productId),
    enabled: !!productId,
  });
};
```

---

## 🎯 State Management

### Using Context API (`src/context/AuthContext.tsx`)

```typescript
import React, { createContext, useContext, useState, useEffect } from 'react';
import { authService, User } from '../services/authService';

interface AuthContextType {
  user: User | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  isAuthenticated: boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({
  children,
}) => {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadUser();
  }, []);

  const loadUser = async () => {
    try {
      const currentUser = await authService.getCurrentUser();
      setUser(currentUser);
    } catch (error) {
      console.error('Error loading user:', error);
    } finally {
      setLoading(false);
    }
  };

  const login = async (email: string, password: string) => {
    const response = await authService.login({ email, password });
    if (response.success) {
      setUser(response.data.user);
    } else {
      throw new Error(response.message || 'Login failed');
    }
  };

  const logout = async () => {
    await authService.logout();
    setUser(null);
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        loading,
        login,
        logout,
        isAuthenticated: !!user,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider');
  }
  return context;
};
```

---

## ⚠️ Error Handling

### Error Handler Utility (`src/utils/errorHandler.ts`)

```typescript
import { AxiosError } from 'axios';

export const handleApiError = (error: any): string => {
  if (error instanceof AxiosError) {
    if (error.response) {
      // Server responded with error
      const message = error.response.data?.message || error.response.data?.error?.message;
      return message || 'An error occurred';
    } else if (error.request) {
      // Request made but no response
      return 'No response from server. Please check your internet connection.';
    }
  }
  return error.message || 'An unexpected error occurred';
};
```

---

## 📝 Best Practices

### 1. Environment Configuration

Create `src/config/env.ts`:

```typescript
export const config = {
  API_BASE_URL: __DEV__
    ? 'http://localhost:8000'
    : 'https://your-production-url.com',
  API_TIMEOUT: 30000,
};
```

### 2. Type Safety

Always define TypeScript interfaces for API responses to ensure type safety.

### 3. Caching Strategy

- Use React Query for automatic caching and background refetching
- Cache product lists for 5 minutes
- Cache categories for 1 hour
- Invalidate cache on mutations (add to cart, create order)

### 4. Loading States

Always show loading indicators during API calls to improve UX.

### 5. Error Messages

Display user-friendly error messages, not technical error details.

### 6. Offline Support

Consider implementing offline support using React Query's persistence features.

---

## 🔄 Data Flow: Admin Panel → Mobile App

When an admin adds/updates a product in the admin panel:

1. **Admin Panel** → Creates/updates product via `/admin/products`
2. **Backend** → Saves to database
3. **Mobile App** → Fetches products via `/api/v1/products`
4. **React Query** → Caches the data
5. **UI Updates** → Product appears in the app

### Polling for Updates (Optional)

```typescript
// Poll every 30 seconds for new products
const { data } = useQuery({
  queryKey: ['products'],
  queryFn: () => productService.getProducts(),
  refetchInterval: 30000, // 30 seconds
});
```

---

## 🎨 Complete Example: Home Screen

```typescript
import React from 'react';
import { View, ScrollView, StyleSheet } from 'react-native';
import { useProducts } from '../hooks/useProducts';
import { useOffers } from '../hooks/useOffers';
import { BannerCarousel } from '../components/BannerCarousel';
import { ProductGrid } from '../components/ProductGrid';
import { CategoryList } from '../components/CategoryList';

export const HomeScreen: React.FC = () => {
  const { data: offers } = useOffers();
  const { data: productsData } = useProducts({ featured: true, limit: 10 });

  return (
    <ScrollView style={styles.container}>
      {/* Banner Offers */}
      {offers?.data.banners && (
        <BannerCarousel banners={offers.data.banners} />
      )}

      {/* Categories */}
      <CategoryList />

      {/* Featured Products */}
      {productsData?.data.products && (
        <ProductGrid
          title="Featured Products"
          products={productsData.data.products}
        />
      )}

      {/* Text Offers */}
      {offers?.data.textOffers && (
        <TextOffers offers={offers.data.textOffers} />
      )}
    </ScrollView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f5f5f5',
  },
});
```

---

## ✅ Checklist

- [ ] Install required dependencies (axios, async-storage)
- [ ] Set up API client with authentication
- [ ] Create service files for each API endpoint
- [ ] Implement authentication flow
- [ ] Create product list and detail screens
- [ ] Implement cart functionality
- [ ] Add order creation flow
- [ ] Set up error handling
- [ ] Add loading states
- [ ] Test all API endpoints
- [ ] Configure environment variables
- [ ] Add offline support (optional)

---

This guide provides a complete foundation for integrating your React Native app with the backend API. All endpoints are ready to use, and the data structure matches what the backend returns.

