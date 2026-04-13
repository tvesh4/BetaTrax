from django.db import models
from django.core.exceptions import ValidationError
from django.conf import settings

# class Tester(models.Model):
#     id = models.CharField(primary_key=True)
#     email = models.EmailField(null=True, blank=True, unique=True)

#     def __str__(self):
#         return self.id
    
# class ProductOwner(models.Model):
#     id = models.CharField(primary_key=True)
#     fullName = models.CharField()
#     email = models.EmailField(null=True, blank=True)
#     username = models.CharField()
#     isActive = models.BooleanField()

#     def __str__(self):
#         return self.id
    
# class Developer(models.Model):
#     id = models.CharField(primary_key=True)
#     fullName = models.CharField()
#     email = models.EmailField(null=True, blank=True)
#     username = models.CharField()
#     isActive = models.BooleanField()

#     def __str__(self):
#         return self.id
    
class Product(models.Model):
    id = models.CharField(primary_key=True)
    displayName = models.CharField()
    description = models.CharField()
    currentVersion = models.CharField()
    isActiveBeta = models.BooleanField()
    ownerId = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='ownerId',
        null=True, blank=True
    )
    devId = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='devId',
        null=True, blank=True
    )

    def __str__(self):
        return self.id

class DefectReport(models.Model):
    class Status(models.TextChoices):
        NEW = 'New', 'New'
        OPEN = 'Open', 'Open'
        ASSIGNED = 'Assigned', 'Assigned'
        CLOSED = 'Closed', 'Closed' # Cannot Reproduce, Duplicate, Rejected
        FIXED = 'Fixed', 'Fixed'
        REOPENED = 'Reopened', 'Reopened'
        RESOLVED = 'Resolved', 'Resolved'
    class Severity(models.TextChoices): 
        LOW = 'Low', 'Low'
        MINOR = 'Minor', 'Minor'
        MAJOR = 'Major', 'Major'
        CRITICAL = 'Critical', 'Critical'
    class Priority(models.TextChoices): 
        LOW = 'Low', 'Low'
        MEDIUM = 'Medium', 'Medium'
        HIGH = 'High', 'High'
        CRITICAL = 'Critical', 'Critical'

    id = models.CharField(primary_key=True)
    productId = models.ForeignKey(Product, on_delete=models.SET_DEFAULT, default=None)
    productVersion = models.CharField()
    title = models.CharField()
    description = models.CharField()
    reproductionSteps = models.CharField()
    testerId = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='testerId'
    )
    submittedAt = models.DateTimeField(auto_now_add=True)
    status = models.CharField(
        choices=Status.choices,
        default=Status.NEW,
    )
    severity = models.CharField(choices=Severity.choices, null=True, blank=True)
    priority = models.CharField(choices=Priority.choices, null=True, blank=True)
    # evaluatedById = models.ForeignKey(ProductOwner, on_delete=models.SET_DEFAULT, default=None, null=True, blank=True)
    assignedToId = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='assignedToId')
    parent = models.ForeignKey(
        'self', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='children'
    )

    def clean(self):
        if self.parent and self.id and self.parent.id == self.id:
            raise ValidationError("A report cannot be its own parent.")
        super().clean()

    def __str__(self):
        return self.id
    
class Comment(models.Model):
    id = models.CharField(primary_key=True)
    content = models.CharField()
    createdAt = models.DateTimeField(auto_now_add=True)
    defectReportId = models.ForeignKey(
        'DefectReport', 
        on_delete=models.CASCADE, 
        related_name='comments'
    )
    authorId = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='authorId')
    # authorType = ?

    class Meta:
        ordering = ['-createdAt']
    
    def __str__(self):
        return self.id