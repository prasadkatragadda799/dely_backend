# React Native Quick Start Guide

## 🚀 Quick Setup (5 Minutes)

### 1. Install Dependencies

```bash
npm install axios @react-native-async-storage/async-storage
```

### 2. Create API Client

Create `src/services/api.ts`:

```typescript
import axios from 'axios';
import AsyncStorage from '@react-native-async-storage/async-storage';

const API_URL = 'https://your-backend-url.com';

const api = axios.create({
  baseURL: API_URL,
  headers: { 'Content-Type': 'application/json' },
});

// Add token to requests
api.interceptors.request.use(async (config) => {
  const token = await AsyncStorage.getItem('accessToken');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export default api;
```

### 3. Login Example

```typescript
import api from './services/api';
import AsyncStorage from '@react-native-async-storage/async-storage';

const login = async (email: string, password: string) => {
  try {
    const response = await api.post('/api/v1/auth/login', {
      email,
      password,
    });
    
    if (response.data.success) {
      await AsyncStorage.setItem('accessToken', response.data.data.token);
      await AsyncStorage.setItem('refreshToken', response.data.data.refreshToken);
      return response.data;
    }
  } catch (error) {
    console.error('Login error:', error);
    throw error;
  }
};
```

### 4. Fetch Products Example

```typescript
import api from './services/api';

const getProducts = async () => {
  try {
    const response = await api.get('/api/v1/products', {
      params: { page: 1, limit: 20 },
    });
    return response.data.data.products;
  } catch (error) {
    console.error('Error fetching products:', error);
    throw error;
  }
};
```

### 5. Use in Component

```typescript
import React, { useEffect, useState } from 'react';
import { View, FlatList, Text } from 'react-native';
import { getProducts } from './services/productService';

const ProductList = () => {
  const [products, setProducts] = useState([]);

  useEffect(() => {
    loadProducts();
  }, []);

  const loadProducts = async () => {
    const data = await getProducts();
    setProducts(data);
  };

  return (
    <FlatList
      data={products}
      renderItem={({ item }) => (
        <View>
          <Text>{item.name}</Text>
          <Text>₹{item.sellingPrice}</Text>
        </View>
      )}
    />
  );
};
```

## 📡 Key API Endpoints

### Authentication
- `POST /api/v1/auth/login` - Login
- `POST /api/v1/auth/register` - Register
- `POST /api/v1/auth/refresh-token` - Refresh token
- `POST /api/v1/auth/logout` - Logout

### Products
- `GET /api/v1/products` - List products
- `GET /api/v1/products/{id}` - Get product by ID
- `GET /api/v1/products/slug/{slug}` - Get product by slug
- `GET /api/v1/products/featured` - Get featured products

### Categories
- `GET /api/v1/categories` - Get categories (tree structure)

### Offers
- `GET /api/v1/offers` - Get active offers

### Cart
- `GET /api/v1/cart` - Get cart
- `POST /api/v1/cart/add` - Add to cart
- `PUT /api/v1/cart/items/{id}` - Update cart item
- `DELETE /api/v1/cart/items/{id}` - Remove from cart

### Orders
- `POST /api/v1/orders` - Create order
- `GET /api/v1/orders` - Get user orders
- `GET /api/v1/orders/{id}` - Get order details

## 🔑 Important Notes

1. **Always include token** in Authorization header for protected routes
2. **Handle 401 errors** - Token expired, refresh or logout
3. **Product structure** - Now includes `brand`, `company`, `category` objects
4. **Discount calculation** - Already calculated in response (`discount` field)
5. **Images** - Use `images` array with `isPrimary` flag

## 🎯 Next Steps

1. Read the full integration guide: `REACT_NATIVE_INTEGRATION_GUIDE.md`
2. Implement authentication flow
3. Create product screens
4. Add cart functionality
5. Implement order creation

