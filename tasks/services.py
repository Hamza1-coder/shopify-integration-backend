import pandas as pd
import csv
from io import StringIO
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from django.db import transaction
from products.models import Product, InventoryLog
import logging

logger = logging.getLogger(__name__)

class CSVImportService:
    """Service for importing product data from CSV."""
    
    def __init__(self):
        self.required_columns = ['name', 'sku', 'price', 'inventory_quantity']
    
    def import_from_csv_content(self, csv_content):
        """Import products from CSV content."""
        try:
            # Parse CSV
            df = pd.read_csv(StringIO(csv_content))
            
            # Validate columns
            missing_columns = set(self.required_columns) - set(df.columns)
            if missing_columns:
                raise ValueError(f"Missing required columns: {missing_columns}")
            
            results = {
                'total_rows': len(df),
                'imported': 0,
                'updated': 0,
                'errors': []
            }
            
            with transaction.atomic():
                for index, row in df.iterrows():
                    try:
                        self._process_row(row, results)
                    except Exception as e:
                        error_msg = f"Row {index + 1}: {str(e)}"
                        results['errors'].append(error_msg)
                        logger.error(error_msg)
            
            logger.info(f"CSV import completed: {results}")
            return results
            
        except Exception as e:
            logger.error(f"CSV import failed: {str(e)}")
            raise
    
    def _process_row(self, row, results):
        """Process a single CSV row."""
        sku = str(row['sku']).strip()
        name = str(row['name']).strip()
        price = float(row['price'])
        inventory_quantity = int(row['inventory_quantity'])
        description = str(row.get('description', '')).strip()
        
        # Validate data
        if not sku or not name:
            raise ValueError("SKU and name are required")
        
        if price < 0:
            raise ValueError("Price cannot be negative")
        
        if inventory_quantity < 0:
            raise ValueError("Inventory quantity cannot be negative")
        
        # Create or update product
        product, created = Product.objects.get_or_create(
            sku=sku,
            defaults={
                'name': name,
                'price': price,
                'inventory_quantity': inventory_quantity,
                'description': description,
                'is_active': True
            }
        )
        
        if created:
            results['imported'] += 1
            logger.info(f"Imported new product: {sku}")
        else:
            # Update existing product
            old_inventory = product.inventory_quantity
            product.name = name
            product.price = price
            product.inventory_quantity = inventory_quantity
            product.description = description
            product.save()
            
            # Log inventory change if different
            if old_inventory != inventory_quantity:
                InventoryLog.objects.create(
                    product=product,
                    old_quantity=old_inventory,
                    new_quantity=inventory_quantity,
                    change_reason="CSV import update"
                )
            
            results['updated'] += 1
            logger.info(f"Updated existing product: {sku}")

class DataValidationService:
    """Service for validating product data."""
    
    def validate_all_products(self):
        """Validate all products and return validation results."""
        results = {
            'total_products': 0,
            'valid_products': 0,
            'issues': []
        }
        
        products = Product.objects.all()
        results['total_products'] = products.count()
        
        for product in products:
            issues = self._validate_product(product)
            if issues:
                results['issues'].extend(issues)
            else:
                results['valid_products'] += 1
        
        logger.info(f"Data validation completed: {results}")
        return results
    
    def _validate_product(self, product):
        """Validate a single product."""
        issues = []
        
        # Check for empty or invalid fields
        if not product.name.strip():
            issues.append(f"Product {product.sku}: Empty name")
        
        if not product.sku.strip():
            issues.append(f"Product {product.id}: Empty SKU")
        
        if product.price < 0:
            issues.append(f"Product {product.sku}: Negative price")
        
        if product.inventory_quantity < 0:
            issues.append(f"Product {product.sku}: Negative inventory")
        
        # Check for duplicate SKUs
        duplicate_count = Product.objects.filter(sku=product.sku).count()
        if duplicate_count > 1:
            issues.append(f"Product {product.sku}: Duplicate SKU found")
        
        return issues

class ReportGenerationService:
    """Service for generating reports."""
    
    def generate_inventory_report(self):
        """Generate comprehensive inventory report."""
        from django.db.models import Sum, Avg, Count
        
        # Basic statistics
        stats = Product.objects.filter(is_active=True).aggregate(
            total_products=Count('id'),
            total_inventory_value=Sum('price') * Sum('inventory_quantity'),
            avg_price=Avg('price'),
            total_inventory_items=Sum('inventory_quantity')
        )
        
        # Low stock products
        low_stock_products = Product.objects.filter(
            is_active=True,
            inventory_quantity__lt=10
        ).values('name', 'sku', 'inventory_quantity', 'price')
        
        # High value products
        high_value_products = Product.objects.filter(
            is_active=True,
            price__gte=100
        ).order_by('-price')[:10].values('name', 'sku', 'price')
        
        # Recent inventory changes
        recent_changes = InventoryLog.objects.select_related('product').order_by(
            '-timestamp'
        )[:20].values(
            'product__name', 'product__sku', 'old_quantity', 
            'new_quantity', 'change_reason', 'timestamp'
        )
        
        report = {
            'generated_at': timezone.now().isoformat(),
            'statistics': stats,
            'low_stock_products': list(low_stock_products),
            'high_value_products': list(high_value_products),
            'recent_inventory_changes': list(recent_changes),
        }
        
        logger.info("Inventory report generated successfully")
        return report
    
    def send_report_email(self, report_data, recipient_email=None):
        """Send report via email."""
        recipient = recipient_email or settings.DEFAULT_FROM_EMAIL
        
        # Create email content
        subject = f"Daily Inventory Report - {timezone.now().strftime('%Y-%m-%d')}"
        
        # Format the report as text
        message = self._format_report_as_text(report_data)
        
        try:
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[recipient],
                fail_silently=False,
            )
            
            logger.info(f"Report email sent to {recipient}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send report email: {str(e)}")
            return False
    
    def _format_report_as_text(self, report_data):
        """Format report data as readable text."""
        stats = report_data['statistics']
        
        message = f"""
Daily Inventory Report
Generated: {report_data['generated_at']}

=== SUMMARY STATISTICS ===
Total Products: {stats['total_products']}
Total Inventory Items: {stats['total_inventory_items']}
Average Price: ${stats['avg_price']:.2f}

=== LOW STOCK ALERTS ===
"""
        
        low_stock = report_data['low_stock_products']
        if low_stock:
            for product in low_stock:
                message += f"- {product['name']} ({product['sku']}): {product['inventory_quantity']} remaining\n"
        else:
            message += "No low stock products found.\n"
        
        message += f"""
=== HIGH VALUE PRODUCTS ===
"""
        
        for product in report_data['high_value_products']:
            message += f"- {product['name']} ({product['sku']}): ${product['price']:.2f}\n"
        
        message += f"""
=== RECENT INVENTORY CHANGES ===
"""
        
        for change in report_data['recent_inventory_changes'][:10]:
            message += f"- {change['product__name']}: {change['old_quantity']} → {change['new_quantity']} ({change['change_reason']})\n"
        
        return message
