from django.db import models

class Tester(models.Model):
    id = models.CharField(primary_key=True)
    email = models.EmailField(null=True, blank=True, unique=True)

    def __str__(self):
        return self.id
    
class ProductOwner(models.Model):
    id = models.CharField(primary_key=True)
    fullName = models.CharField()
    email = models.EmailField(null=True, blank=True)
    username = models.CharField()
    isActive = models.BooleanField()

    def __str__(self):
        return self.id
    
class Developer(models.Model):
    id = models.CharField(primary_key=True)
    fullName = models.CharField()
    email = models.EmailField(null=True, blank=True)
    username = models.CharField()
    isActive = models.BooleanField()

    def __str__(self):
        return self.id
    
class Product(models.Model):
    id = models.CharField(primary_key=True)
    displayName = models.CharField()
    description = models.CharField()
    currentVersion = models.CharField()
    isActiveBeta = models.BooleanField()
    ownerId = models.ForeignKey(ProductOwner, on_delete=models.SET_DEFAULT, default=None, null=True, blank=True)
    devId = models.ForeignKey(Developer, on_delete=models.SET_DEFAULT, default=None, null=True, blank=True)

    def __str__(self):
        return self.id

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

    id = models.CharField(primary_key=True)
    productId = models.ForeignKey(Product, on_delete=models.SET_DEFAULT, default=None)
    productVersion = models.CharField()
    title = models.CharField()
    description = models.CharField()
    reproductionSteps = models.CharField()
    testerId = models.ForeignKey(Tester, on_delete=models.SET_DEFAULT, default=None)
    testerEmail = models.EmailField(null=True, blank=True)
    submittedAt = models.DateTimeField(auto_now_add=True)
    status = models.CharField(
        choices=Status.choices,
        default=Status.NEW,
    )
    severity = models.IntegerField(choices=Severity.choices, null=True, blank=True)
    priority = models.IntegerField(choices=Priority.choices, null=True, blank=True)
    evaluatedById = models.ForeignKey(ProductOwner, on_delete=models.SET_DEFAULT, default=None, null=True, blank=True)
    assignedToId = models.ForeignKey(Developer, on_delete=models.SET_DEFAULT, default=None, null=True, blank=True)

    def __str__(self):
        return self.title