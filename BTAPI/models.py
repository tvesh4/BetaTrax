from django.db import models

class Tester(models.Model):
    id = models.CharField(primary_key=True)
    email = models.EmailField(null=True, blank=True)

    def __str__(self):
        return self.id
    
class Product(models.Model):
    id = models.IntegerField(primary_key=True)
    displayName = models.CharField()
    description = models.CharField()
    currentVersion = models.CharField()
    isActiveBeta = models.BooleanField()

    def __str__(self):
        return self.displayName
    
class ProductOwner(models.Model):
    id = models.IntegerField(primary_key=True)
    fullName = models.CharField()
    email = models.EmailField(null=True, blank=True)
    username = models.CharField()
    isActive = models.BooleanField()
    productId = models.ForeignKey(Product, on_delete=models.SET_DEFAULT, default=None, null=True, blank=True)

    def __str__(self):
        return self.username
    
class Developer(models.Model):
    id = models.IntegerField(primary_key=True)
    productId = models.ForeignKey(Product, on_delete=models.SET_DEFAULT, default=None, null=True, blank=True)
    fullName = models.CharField()
    email = models.EmailField(null=True, blank=True)
    username = models.CharField()
    isActive = models.BooleanField()

    def __str__(self):
        return self.username

class DefectReport(models.Model):
    class Status(models.TextChoices):
        NEW = 'NEW', 'New'
        OPEN = 'OPEN', 'Open'
        ASSIGNED = 'ASSIGNED', 'Assigned'
        FIXED = 'FIXED', 'Fixed'
        RESOLVED = 'RESOLVED', 'Resolved'
    class Severity(models.IntegerChoices): 
        LOW = 1, 'Low'
        MINOR = 2, 'Minor'
        MAJOR = 3, 'Major'
        CRITICAL = 4, 'Critical'
    class Priority(models.IntegerChoices): 
        LOW = 1, 'Low'
        MEDIUM = 2, 'Medium'
        HIGH = 3, 'High'
        CRITICAL = 4, 'Critical'

    id = models.IntegerField(primary_key=True)
    testerId = models.ForeignKey(Tester, on_delete=models.SET_DEFAULT, default=None)
    title = models.CharField()
    description = models.CharField()
    reproductionSteps = models.CharField()
    evaluatedById = models.ForeignKey(ProductOwner, on_delete=models.SET_DEFAULT, default=None, null=True, blank=True)
    status = models.CharField(
        choices=Status.choices,
        default=Status.NEW,
    )
    severity = models.IntegerField(choices=Severity.choices, default=Severity.LOW)
    priority = models.IntegerField(choices=Priority.choices, default=Priority.LOW)
    submittedAt = models.DateTimeField(auto_now_add=True)
    testerEmail = models.EmailField(null=True, blank=True)
    productId = models.ForeignKey(Product, on_delete=models.SET_DEFAULT, default=None)
    assignedToId = models.ForeignKey(Developer, on_delete=models.SET_DEFAULT, default=None, null=True, blank=True)

    def __str__(self):
        return self.title