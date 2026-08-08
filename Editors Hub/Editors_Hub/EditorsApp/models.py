from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from django.db.models import Avg
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from datetime import timedelta

class Category(models.Model):
    name = models.CharField(max_length=50)

    def __str__(self):
        return self.name 


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    phone = models.CharField(max_length=10)
    profile_pic = models.ImageField(upload_to='user_profile/', blank=True, null=True, default='default.png')

    GENDER_CHOICES = [
        ('M', 'Male'),
        ('F', 'Female'),
        ('O', 'Other'),
    ]

    gender = models.CharField(max_length=10, choices=GENDER_CHOICES, blank=True)
    age = models.PositiveIntegerField(blank=True, null=True)

    email_otp = models.CharField(max_length=6, blank=True, null=True)
    otp_created_at = models.DateTimeField(blank=True, null=True)
    is_email_verified = models.BooleanField(default=False)

    def __str__(self):
        return self.user.username
    

class EditorProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)

    name = models.CharField(max_length=100)
    age = models.IntegerField()

    GENDER_CHOICES = [
        ('M', 'Male'),
        ('F', 'Female'),
        ('O', 'Other')
    ]
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES)

    email = models.EmailField()
    phone = models.CharField(max_length=10)
    price = models.CharField(max_length=50)

    category = models.ManyToManyField('Category')

    profile_image = models.ImageField(
        upload_to='editors_profile/',
        blank=True,
        null=True,
        default='default.png'
    )

    # ⭐ NEW FIELDS YOU REQUESTED
    bio = models.TextField(blank=True)

    language = models.ManyToManyField('Language', blank=True)
    experience_years = models.PositiveIntegerField(default=0)

    softwares = models.CharField(max_length=255, blank=True)
    # Example: "Photoshop, Premiere Pro, Blender"

    address = models.TextField(blank=True)

    id_proof = models.FileField(upload_to='id_proofs/', blank=True, null=True)

    portfolio = models.URLField(blank=True)

    # STATUS SYSTEM (already good)
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')

    MODE_CHOICES = [
        ('active', 'Active'),
        ('busy', 'Working'),
        ('offline', 'Offline'),
    ]
    mode = models.CharField(max_length=10, choices=MODE_CHOICES, default='active')

    rejection_reason = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.user.username

    @property
    def average_rating(self):
        return self.ratings.aggregate(avg=Avg('rating'))['avg'] or 0

    @property
    def total_reviews(self):
        return self.ratings.count()
    

class Language(models.Model):
    name = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.name
    


class Message(models.Model):
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_messages')
    receiver = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_messages')
    content = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    is_seen = models.BooleanField(default=False)
    is_read = models.BooleanField(default=False)
    is_unsent = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.sender} → {self.receiver}"
    

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)


class Work(models.Model):
    editor = models.ForeignKey(EditorProfile, on_delete=models.CASCADE, related_name='works')
    media = models.FileField(upload_to='works/')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Work {self.id} - {self.editor.user.username}"

    @property
    def is_video(self):
        return self.media.url.lower().endswith(('.mp4', '.webm', '.mov'))
    

class Rating(models.Model):
    editor = models.ForeignKey(EditorProfile, on_delete=models.CASCADE, related_name='ratings')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    rating = models.IntegerField(
    validators=[MinValueValidator(1), MaxValueValidator(5)]
)

    comment = models.TextField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('editor', 'user')

    def __str__(self):
        return f"{self.user} → {self.editor} ({self.rating})"
    


class SupportMessage(models.Model):

    STATUS_CHOICES = (
        ('Pending', 'Pending'),
        ('Replied', 'Replied'),
        ('Closed', 'Closed'),
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE)

    subject = models.CharField(max_length=200)

    message = models.TextField()

    created_at = models.DateTimeField(auto_now_add=True)

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='Pending'
    )

    def __str__(self):
        return f"{self.user.username} - {self.subject}"
    

class EditRequest(models.Model):

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
        ('finished', 'Finished'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_requests')
    editor = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_requests')

    # ✅ ADD THIS
    category = models.ForeignKey('Category', on_delete=models.SET_NULL, null=True, blank=True)

    message = models.TextField(blank=True, null=True)
    file = models.FileField(upload_to='edit_requests/', null=True, blank=True)

    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')

    drive_link = models.URLField(blank=True, null=True)
    amount = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user} → {self.editor} ({self.status})"