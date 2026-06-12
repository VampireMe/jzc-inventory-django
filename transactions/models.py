from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from access.models import Department
from inventory.models import Stock

#contains suppliers
class Supplier(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=150)
    department = models.ForeignKey(Department, on_delete=models.PROTECT, related_name='suppliers')
    phone = models.CharField(max_length=12, unique=True)
    address = models.CharField(max_length=200)
    email = models.EmailField(max_length=254, unique=True)
    gstin = models.CharField(max_length=15, unique=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_suppliers'
    )
    updated_at = models.DateTimeField(auto_now=True)
    is_deleted = models.BooleanField(default=False)

    def __str__(self):
	    return self.name


#contains the purchase bills made
class PurchaseBill(models.Model):
    billno = models.AutoField(primary_key=True)
    time = models.DateTimeField(auto_now=True)
    department = models.ForeignKey(Department, on_delete=models.PROTECT, related_name='purchase_bills')
    supplier = models.ForeignKey(Supplier, on_delete = models.CASCADE, related_name='purchasesupplier')
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='purchase_bills'
    )

    def __str__(self):
	    return "Bill no: " + str(self.billno)

    def get_items_list(self):
        return PurchaseItem.objects.filter(billno=self)

    def get_total_price(self):
        purchaseitems = PurchaseItem.objects.filter(billno=self)
        total = 0
        for item in purchaseitems:
            total += item.totalprice
        return total

#contains the purchase stocks made
class PurchaseItem(models.Model):
    billno = models.ForeignKey(PurchaseBill, on_delete = models.CASCADE, related_name='purchasebillno')
    stock = models.ForeignKey(Stock, on_delete = models.CASCADE, related_name='purchaseitem')
    quantity = models.IntegerField(default=1, validators=[MinValueValidator(0), MaxValueValidator(1000000)])
    perprice = models.IntegerField(default=1, validators=[MinValueValidator(0), MaxValueValidator(1000000)])
    totalprice = models.IntegerField(default=1, validators=[MinValueValidator(0), MaxValueValidator(1000000000)])

    def __str__(self):
	    return "Bill no: " + str(self.billno.billno) + ", Item = " + self.stock.name

#contains the other details in the purchases bill
class PurchaseBillDetails(models.Model):
    billno = models.ForeignKey(PurchaseBill, on_delete = models.CASCADE, related_name='purchasedetailsbillno')
    
    eway = models.CharField(max_length=50, blank=True, null=True)    
    veh = models.CharField(max_length=50, blank=True, null=True)
    destination = models.CharField(max_length=50, blank=True, null=True)
    po = models.CharField(max_length=50, blank=True, null=True)
    
    cgst = models.CharField(max_length=50, blank=True, null=True)
    sgst = models.CharField(max_length=50, blank=True, null=True)
    igst = models.CharField(max_length=50, blank=True, null=True)
    cess = models.CharField(max_length=50, blank=True, null=True)
    tcs = models.CharField(max_length=50, blank=True, null=True)
    total = models.IntegerField(default=0, validators=[MinValueValidator(0), MaxValueValidator(1000000000)])

    def __str__(self):
	    return "Bill no: " + str(self.billno.billno)


#contains the sale bills made
class SaleBill(models.Model):
    billno = models.AutoField(primary_key=True)
    time = models.DateTimeField(auto_now=True)
    department = models.ForeignKey(Department, on_delete=models.PROTECT, related_name='sale_bills')

    name = models.CharField(max_length=150)
    phone = models.CharField(max_length=12)
    address = models.CharField(max_length=200)
    email = models.EmailField(max_length=254)
    gstin = models.CharField(max_length=15)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='sale_bills'
    )

    def __str__(self):
	    return "Bill no: " + str(self.billno)

    def get_items_list(self):
        return SaleItem.objects.filter(billno=self)
        
    def get_total_price(self):
        saleitems = SaleItem.objects.filter(billno=self)
        total = 0
        for item in saleitems:
            total += item.totalprice
        return total

#contains the sale stocks made
class SaleItem(models.Model):
    billno = models.ForeignKey(SaleBill, on_delete = models.CASCADE, related_name='salebillno')
    stock = models.ForeignKey(Stock, on_delete = models.CASCADE, related_name='saleitem')
    quantity = models.IntegerField(default=1, validators=[MinValueValidator(0), MaxValueValidator(1000000)])
    perprice = models.IntegerField(default=1, validators=[MinValueValidator(0), MaxValueValidator(1000000)])
    totalprice = models.IntegerField(default=1, validators=[MinValueValidator(0), MaxValueValidator(1000000000)])

    def __str__(self):
	    return "Bill no: " + str(self.billno.billno) + ", Item = " + self.stock.name

#contains the other details in the sales bill
class SaleBillDetails(models.Model):
    billno = models.ForeignKey(SaleBill, on_delete = models.CASCADE, related_name='saledetailsbillno')
    
    eway = models.CharField(max_length=50, blank=True, null=True)    
    veh = models.CharField(max_length=50, blank=True, null=True)
    destination = models.CharField(max_length=50, blank=True, null=True)
    po = models.CharField(max_length=50, blank=True, null=True)
    
    cgst = models.CharField(max_length=50, blank=True, null=True)
    sgst = models.CharField(max_length=50, blank=True, null=True)
    igst = models.CharField(max_length=50, blank=True, null=True)
    cess = models.CharField(max_length=50, blank=True, null=True)
    tcs = models.CharField(max_length=50, blank=True, null=True)
    total = models.IntegerField(default=0, validators=[MinValueValidator(0), MaxValueValidator(1000000000)])

    def __str__(self):
	    return "Bill no: " + str(self.billno.billno)
