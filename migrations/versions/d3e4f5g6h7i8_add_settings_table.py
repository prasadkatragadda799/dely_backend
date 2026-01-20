"""add settings table

Revision ID: d3e4f5g6h7i8
Revises: c2d3e4f5g6h7
Create Date: 2026-01-20 15:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'd3e4f5g6h7i8'
down_revision = 'c2d3e4f5g6h7'
branch_labels = None
depends_on = None


def upgrade():
    # Create settings table
    op.create_table(
        'settings',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('key', sa.String(length=100), nullable=False, unique=True),
        sa.Column('value', postgresql.JSONB, nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()'))
    )
    
    # Create index on key
    op.create_index('idx_settings_key', 'settings', ['key'], unique=True)
    
    # Insert default settings
    op.execute("""
        INSERT INTO settings (id, key, value, created_at, updated_at) VALUES
        (gen_random_uuid(), 'general', '{"appName": "Dely B2B", "appLogoUrl": null, "contactEmail": "support@dely.com", "contactPhone": "+91 1800 123 4567", "businessAddress": "123 Business Park, Mumbai, Maharashtra 400001"}', now(), now()),
        (gen_random_uuid(), 'payment', '{"creditEnabled": true, "upiEnabled": true, "bankTransferEnabled": true, "cashOnDeliveryEnabled": false, "defaultCreditLimit": 50000, "paymentTermsDays": 30}', now(), now()),
        (gen_random_uuid(), 'delivery', '{"standardDeliveryCharge": 100, "freeDeliveryThreshold": 5000, "deliveryTimeSlots": "Morning: 9 AM - 12 PM\\nAfternoon: 12 PM - 4 PM\\nEvening: 4 PM - 8 PM", "serviceablePincodes": ["400001", "400002", "400003"]}', now(), now()),
        (gen_random_uuid(), 'tax', '{"defaultGstRate": 18, "categoryGstRates": []}', now(), now()),
        (gen_random_uuid(), 'notifications', '{"emailTemplates": {"orderConfirmation": "Dear {customer_name},\\n\\nYour order #{order_number} has been confirmed.\\nTotal Amount: ₹{total_amount}\\n\\nThank you for your business!", "orderShipped": "Dear {customer_name},\\n\\nYour order #{order_number} has been shipped.\\nTracking Number: {tracking_number}\\n\\nExpected delivery: {delivery_date}", "orderDelivered": "Dear {customer_name},\\n\\nYour order #{order_number} has been delivered successfully.\\n\\nThank you for your business!", "orderCancelled": "Dear {customer_name},\\n\\nYour order #{order_number} has been cancelled.\\nReason: {cancellation_reason}\\n\\nWe apologize for any inconvenience."}, "smsTemplates": {"orderConfirmation": "Your order #{order_number} for ₹{total_amount} has been confirmed. Thank you!", "orderShipped": "Your order #{order_number} has been shipped. Track: {tracking_number}", "orderDelivered": "Your order #{order_number} has been delivered successfully. Thank you!", "orderCancelled": "Your order #{order_number} has been cancelled. Reason: {cancellation_reason}"}}', now(), now());
    """)


def downgrade():
    # Drop index
    op.drop_index('idx_settings_key', table_name='settings')
    
    # Drop table
    op.drop_table('settings')
