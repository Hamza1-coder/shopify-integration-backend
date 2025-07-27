from celery import shared_task, chain, group
from django.utils import timezone
from django.conf import settings
from .models import TaskExecution
from .services import CSVImportService, DataValidationService, ReportGenerationService
import logging

logger = logging.getLogger(__name__)

# Mock CSV data for testing
MOCK_CSV_DATA = """name,sku,price,inventory_quantity,description
iPhone 14,IP14-128,799.99,50,Latest iPhone model with 128GB storage
Samsung Galaxy S23,SGS23-256,699.99,30,Premium Android phone with 256GB storage
MacBook Air M2,MBA-M2-256,1199.99,15,Lightweight laptop with M2 chip
Dell XPS 13,XPS13-512,999.99,20,Premium ultrabook with 512GB SSD
iPad Pro 11,IPP11-128,799.99,25,Professional tablet with M2 chip
"""

@shared_task(bind=True)
def import_csv_data(self, csv_content=None):
    """Task 1: Import mock product data from CSV."""
    task_execution = TaskExecution.objects.create(task_type='import_csv')
    task_execution.mark_as_running()
    
    try:
        csv_service = CSVImportService()
        
        # Use provided CSV content or mock data
        content = csv_content or MOCK_CSV_DATA
        result = csv_service.import_from_csv_content(content)
        
        task_execution.mark_as_completed(result)
        logger.info(f"CSV import task completed: {result}")
        
        return {
            'task_id': task_execution.id,
            'status': 'completed',
            'result': result
        }
        
    except Exception as exc:
        error_msg = str(exc)
        task_execution.mark_as_failed(error_msg)
        logger.error(f"CSV import task failed: {error_msg}")
        
        raise self.retry(exc=exc, countdown=60, max_retries=3)

@shared_task(bind=True)
def validate_imported_data(self, import_result=None):
    """Task 2: Validate imported data and update inventory quantities."""
    task_execution = TaskExecution.objects.create(task_type='validate_data')
    task_execution.mark_as_running()
    
    try:
        validation_service = DataValidationService()
        result = validation_service.validate_all_products()
        
        # Update inventory for products with issues (example logic)
        if result['issues']:
            logger.warning(f"Found {len(result['issues'])} validation issues")
            # Here you could implement logic to fix common issues
        
        task_execution.mark_as_completed(result)
        logger.info(f"Data validation task completed: {result}")
        
        return {
            'task_id': task_execution.id,
            'status': 'completed',
            'result': result,
            'import_result': import_result
        }
        
    except Exception as exc:
        error_msg = str(exc)
        task_execution.mark_as_failed(error_msg)
        logger.error(f"Data validation task failed: {error_msg}")
        
        raise self.retry(exc=exc, countdown=60, max_retries=3)

@shared_task(bind=True)
def generate_and_send_report(self, validation_result=None):
    """Task 3: Generate report and send email."""
    task_execution = TaskExecution.objects.create(task_type='generate_report')
    task_execution.mark_as_running()
    
    try:
        report_service = ReportGenerationService()
        
        # Generate comprehensive report
        report_data = report_service.generate_inventory_report()
        
        # Add validation results if available
        if validation_result:
            report_data['validation_summary'] = validation_result.get('result', {})
        
        # Send email report
        email_sent = report_service.send_report_email(report_data)
        
        result = {
            'report_generated': True,
            'email_sent': email_sent,
            'report_summary': {
                'total_products': report_data['statistics']['total_products'],
                'low_stock_count': len(report_data['low_stock_products']),
                'high_value_count': len(report_data['high_value_products'])
            }
        }
        
        task_execution.mark_as_completed(result)
        logger.info(f"Report generation task completed: {result}")
        
        return {
            'task_id': task_execution.id,
            'status': 'completed',
            'result': result
        }
        
    except Exception as exc:
        error_msg = str(exc)
        task_execution.mark_as_failed(error_msg)
        logger.error(f"Report generation task failed: {error_msg}")
        
        raise self.retry(exc=exc, countdown=60, max_retries=3)

@shared_task
def nightly_task_chain():
    """Execute the complete nightly task chain."""
    chain_execution = TaskExecution.objects.create(task_type='nightly_chain')
    chain_execution.mark_as_running()
    
    try:
        # Create and execute the task chain
        job = chain(
            import_csv_data.s(),
            validate_imported_data.s(),
            generate_and_send_report.s()
        )
        
        # Execute the chain
        result = job.apply_async()
        
        # Wait for completion (in production, you might want to handle this differently)
        final_result = result.get(timeout=300)  # 5 minute timeout
        
        chain_execution.mark_as_completed({
            'chain_completed': True,
            'final_result': final_result
        })
        
        logger.info("Nightly task chain completed successfully")
        
    except Exception as e:
        error_msg = str(e)
        chain_execution.mark_as_failed(error_msg)
        logger.error(f"Nightly task chain failed: {error_msg}")

# Individual task for manual execution
@shared_task
def refresh_product_embeddings():
    """Refresh AI embeddings for all products."""
    from ai_services.services import AISearchService
    
    try:
        ai_service = AISearchService()
        embeddings = ai_service._generate_product_embeddings()
        
        logger.info(f"Refreshed embeddings for {len(embeddings)} products")
        return {
            'status': 'completed',
            'embeddings_count': len(embeddings)
        }
        
    except Exception as e:
        logger.error(f"Failed to refresh embeddings: {str(e)}")
        raise

@shared_task
def cleanup_old_data():
    """Clean up old logs and temporary data."""
    from products.models import InventoryLog
    from datetime import timedelta
    
    try:
        # Clean up old inventory logs (older than 90 days)
        cutoff_date = timezone.now() - timedelta(days=90)
        deleted_logs = InventoryLog.objects.filter(
            timestamp__lt=cutoff_date
        ).delete()[0]
        
        # Clean up old task executions (older than 30 days)
        task_cutoff = timezone.now() - timedelta(days=30)
        deleted_tasks = TaskExecution.objects.filter(
            created_at__lt=task_cutoff,
            status='completed'
        ).delete()[0]
        
        result = {
            'deleted_inventory_logs': deleted_logs,
            'deleted_task_executions': deleted_tasks
        }
        
        logger.info(f"Cleanup completed: {result}")
        return result
        
    except Exception as e:
        logger.error(f"Cleanup task failed: {str(e)}")
        raise
