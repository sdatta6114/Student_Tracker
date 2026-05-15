from django.db import models

class superadmin(models.Model):
    email = models.EmailField(unique=True)
    password = models.CharField(max_length=100)
    class Meta:
        db_table = "superadmin"

class adm(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    password = models.CharField(max_length=100)
    priv = models.CharField(max_length=100, default="") # Consolidated field
    appr = models.IntegerField(default=0) # 0: Pending, 1: Approved
    class Meta:
        db_table = "adm"

class student(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    pwd = models.CharField(max_length=100)
    # roll and dept removed [cite: 556]
    class Meta:
        db_table = "student"
    class Meta:
        db_table = "student"

class aboutinfo(models.Model):
    origin = models.TextField()
    mission = models.TextField()
    vision = models.TextField()
    class Meta:
        db_table = "aboutinfo"

class contactinfo(models.Model):
    address = models.CharField(max_length=255)
    phone = models.CharField(max_length=20)
    email = models.EmailField()
    class Meta:
        db_table = "contactinfo"

class Teacher(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    password = models.CharField(max_length=100)
    is_active = models.BooleanField(default=False) # Admin must allow them to join

class Course(models.Model):
    title = models.CharField(max_length=100)
    description = models.TextField()
    subject_code = models.CharField(max_length=20, unique=True)
    fee = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    is_paid = models.BooleanField(default=False)
    is_free = models.BooleanField(default=False)

class Batch(models.Model):
    batch_number = models.CharField(max_length=50, unique=True)
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    teacher = models.ForeignKey(Teacher, on_delete=models.SET_NULL, null=True)
    class_link = models.URLField(max_length=500, null=True, blank=True)
    is_completed = models.BooleanField(default=False)
    schedule_days = models.CharField(
        max_length=100, 
        help_text="e.g. Mon, Wed, Fri"
    )
    schedule_time = models.TimeField(null=True, blank=True)
    is_completed = models.BooleanField(default=False)
    completion_requested = models.BooleanField(default=False)
    

class Enrollment(models.Model):
    student = models.ForeignKey('student', on_delete=models.CASCADE)
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    batch = models.ForeignKey(Batch, on_delete=models.SET_NULL, null=True, blank=True)
    is_approved = models.BooleanField(default=False)
    total_fee = models.DecimalField(max_digits=10, decimal_places=2)
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    status = models.CharField(max_length=20, default="Ongoing")
    # NEW FIELD: Store payment screenshots
    receipt = models.FileField(upload_to='receipts/', null=True, blank=True)
    is_halted = models.BooleanField(default=False)
    course_rating = models.IntegerField(null=True, blank=True)
    course_feedback = models.TextField(null=True, blank=True)

class Resource(models.Model):
    batch = models.ForeignKey(Batch, on_delete=models.CASCADE)
    title = models.CharField(max_length=100)
    # Changed 'upload_url' to 'upload_to'
    notes = models.FileField(upload_to='notes/') 
    video_url = models.URLField(blank=True)
    video_file = models.FileField(upload_to='videos/', null=True, blank=True)
    live_doc_url = models.URLField(blank=True)
    
class Attendance(models.Model):
    enrollment = models.ForeignKey('Enrollment', on_delete=models.CASCADE)
    date = models.DateField(auto_now_add=True)
    is_present = models.BooleanField(default=False)

class AssignmentSubmission(models.Model):
    enrollment = models.ForeignKey('Enrollment', on_delete=models.CASCADE)
    batch = models.ForeignKey('Batch', on_delete=models.CASCADE)
    file = models.FileField(upload_to='submissions/')
    submitted_at = models.DateTimeField(auto_now_add=True)
    remarks = models.TextField(blank=True, null=True)
    rating = models.IntegerField(blank=True, null=True)
    
class OfficialReceipt(models.Model):
    enrollment = models.ForeignKey('Enrollment', on_delete=models.CASCADE)
    receipt_number = models.CharField(max_length=50, unique=True)
    amount_verified = models.DecimalField(max_digits=10, decimal_places=2)
    payment_date = models.DateField(auto_now_add=True)
    message = models.TextField(blank=True) # e.g., "Partial Payment Received" or "Full Payment"
    

# No need to import .models if this is in your main models.py
# from django.db import models
from django.db import models

class StudentDoubt(models.Model):
    enrollment = models.ForeignKey('Enrollment', on_delete=models.CASCADE)
    batch = models.ForeignKey('Batch', on_delete=models.CASCADE)
    title = models.CharField(max_length=255)
    description = models.TextField()
    # Critical for CSE: allows uploading error logs or code snippets
    screenshot = models.ImageField(upload_to='doubts/', null=True, blank=True)
    is_resolved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

class DoubtReply(models.Model):
    doubt = models.ForeignKey(StudentDoubt, related_name='replies', on_delete=models.CASCADE)
    replied_by_role = models.CharField(max_length=50) # 'teacher' or 'student'
    replied_by_name = models.CharField(max_length=100)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)