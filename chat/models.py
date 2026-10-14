from django.db import models
from django.contrib.auth.models import User


# Create your models here.

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    phone = models.CharField(max_length=20, unique=True)
    public_key = models.TextField(blank=True)
    last_seen = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.user.first_name}({self.phone})"


    
class Message(models.Model):
    sender = models.ForeignKey(User,  on_delete=models.CASCADE, related_name='sent_message')
    receiver = models.ForeignKey(User, on_delete=models.CASCADE, related_name= 'received_message')
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"{self.sender.first_name} to {self.receiver.first_name}:{self.text[:20]}"





class Contact(models.Model):
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='contacts')
    contact = models.ForeignKey(User, on_delete=models.CASCADE, related_name='added_by')

    class Meta:
        unique_together = ('owner', 'contact')

    def __str__(self):
        return f"{self.owner.first_name} -> {self.contact.first_name}"