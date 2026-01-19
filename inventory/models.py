from django.db import models
from core.models import Outlet, Employee

class ProductMaster(models.Model):
    outlet = models.ForeignKey(Outlet, on_delete=models.CASCADE)
    itcode = models.CharField(max_length=50)
    itdesc = models.CharField(max_length=255)
    sprice = models.DecimalField(max_digits=10, decimal_places=2)
    cprice = models.DecimalField(max_digits=10, decimal_places=2)
    asat_date = models.DateField()
    barcode = models.CharField(max_length=100, unique=True)
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('outlet', 'itcode') # One product code per outlet

    def __str__(self):
        return f"{self.itcode} - {self.itdesc}"

class ExcelUploadLog(models.Model):
    outlet = models.ForeignKey(Outlet, on_delete=models.CASCADE)
    uploaded_by = models.ForeignKey('auth.User', on_delete=models.SET_NULL, null=True)
    selected_date = models.DateField()
    upload_timestamp = models.DateTimeField(auto_now_add=True)
    excel_file = models.FileField(upload_to='uploads/excel/%Y/%m/')

class PendingProductApproval(models.Model):
    """ The Temp Table for Manager Confirmation """
    outlet = models.ForeignKey(Outlet, on_delete=models.CASCADE)
    itcode = models.CharField(max_length=50)
    itdesc = models.CharField(max_length=255)
    sprice = models.DecimalField(max_digits=10, decimal_places=2)
    cprice = models.DecimalField(max_digits=10, decimal_places=2)
    asat_date = models.DateField()
    barcode = models.CharField(max_length=100) # Manager assigns this
    status = models.CharField(max_length=20, default='PENDING') # PENDING, APPROVED, REJECTED