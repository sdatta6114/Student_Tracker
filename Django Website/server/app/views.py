from django.shortcuts import render, redirect
from django.http import HttpResponse
from .models import *
from django.db.models import Sum, F
from django.db import IntegrityError
from .models import Batch, Resource
from django.http import FileResponse
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import landscape, A4
import io
import datetime
from .models import Batch, Enrollment, Attendance, AssignmentSubmission
from .models import Enrollment, Course, Batch
import io
import qrcode
from django.http import FileResponse
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import landscape, A4
from reportlab.lib.units import inch
from reportlab.lib.colors import HexColor
from .models import Enrollment
import uuid
from django.db.models import Count, Q
from .models import Enrollment, Course
from .models import Enrollment, Attendance

# --- Home Page ---

def home(request):
    return render(request, 'home.html')

# --- Authentication ---

def login(request):
    email = request.GET.get('email')
    pwd = request.GET.get('password')
    
    if email and pwd:
        # 1. Check Superadmin
        sa = superadmin.objects.filter(email=email, password=pwd).first()
        if sa:
            request.session['role'] = 'superadmin'
            request.session['name'] = 'Super Admin'
            request.session['priv'] = 'about,contact,student'
            return redirect('/home')

        # 2. Check Teacher (New Role)
        t = Teacher.objects.filter(email=email, password=pwd, is_active=True).first()
        if t:
            request.session['role'] = 'teacher'
            request.session['user_id'] = t.id
            request.session['name'] = t.name
            return redirect('/home')

        # 3. Check Admin
        a = adm.objects.filter(email=email, password=pwd, appr=1).first()
        if a:
            request.session['role'] = 'admin'
            request.session['name'] = a.name
            request.session['priv'] = a.priv
            return redirect('/home')

        # 4. Check Student
        st = student.objects.filter(email=email, pwd=pwd).first()
        if st:
            request.session['role'] = 'student'
            request.session['name'] = st.name
            request.session['user_id'] = st.id
            return redirect('/home')
        
        return HttpResponse("Invalid Login or Account Pending Approval")
            
    return render(request, 'login.html')

def logout(request):
    request.session.flush() #
    return redirect('/login')

# --- Admin Functionality ---

from django.shortcuts import render, redirect
from django.http import HttpResponse
from .models import *
from django.db.models import Sum, F
from django.db import IntegrityError  # Crucial for handling duplicate emails

from django.shortcuts import render, redirect
from django.http import HttpResponse
from .models import *
from django.db.models import Sum, F
from django.db import IntegrityError

def admin_dashboard(request):
    # 1. Access Control: Restrict to Admins only
    if request.session.get('role') not in ['admin', 'superadmin']:
        return redirect('/login')
    
    # --- NEW LOGIC: Finish Batch ---
    if request.GET.get('finish_batch') == 'true':
        bid = request.GET.get('bid')
        # Fetch the specific batch
        batch = Batch.objects.get(id=bid)
        
        # 1. Mark batch as finished for Teacher Portal
        batch.is_completed = True
        batch.save()
        
        # 2. Update all student statuses for this specific batch
        Enrollment.objects.filter(batch=batch).update(status="Completed")
        
        print(f"✅ Batch {batch.batch_number} finished. Moved to Teacher Feedback.")
        return redirect('/admin-dash')

    # --- LOGIC SECTION: Processes all Actions ---

    # Logic: Approve Teacher
    if request.GET.get('approve_teacher') == 'true':
        tid = request.GET.get('tid')
    # This updates the teacher's is_active field so they can now pass the login check
        Teacher.objects.filter(id=tid).update(is_active=True)
        return redirect('/admin-dash')

    # Logic: Create New Batch
    if request.GET.get('create_batch') == 'true':
        course_id = request.GET.get('course_id')
        teacher_id = request.GET.get('teacher_id')
        batch_num = request.GET.get('batch_num')
        link = request.GET.get('class_link')
        days = request.GET.get('days')
        time = request.GET.get('time')
        
        Batch.objects.create(
            course_id=course_id,
            teacher_id=teacher_id,
            batch_number=batch_num,
            class_link=link,
            schedule_days=days,
            schedule_time=time,
            is_completed=False
        )
        return redirect('/admin-dash')

    # Logic: Approve Course Enrollment & Assign Batch
    if request.GET.get('approve_enrollment') == 'true':
        eid = request.GET.get('eid')
        bid = request.GET.get('batch_id')
        fee = request.GET.get('final_fee')
        
        Enrollment.objects.filter(id=eid).update(
            batch_id=bid,
            total_fee=fee,
            is_approved=True,
            status="Ongoing"
        )
        return redirect('/admin-dash')

    # Logic: Update Payment status and Amount Paid
    if request.GET.get('update_payment') == 'true':
        eid = request.GET.get('eid')
        new_amt = request.GET.get('amt')
        new_status = request.GET.get('status')
        
        Enrollment.objects.filter(id=eid).update(
            amount_paid=new_amt,
            status=new_status
        )
        return redirect('/admin-dash')
    
    # NEW LOGIC: Halt or Resume Classes with Payment Protection
   # NEW LOGIC: Halt or Resume Classes with Payment Protection
    if request.GET.get('toggle_halt') == 'true':
        eid = request.GET.get('eid')
        enroll = Enrollment.objects.get(id=eid)
        
        # Admin can manually toggle ONLY if payment is not full
        if enroll.amount_paid < enroll.total_fee:
            enroll.is_halted = not enroll.is_halted
            enroll.save()
        else:
            # Safety: If fully paid, class cannot be halted
            enroll.is_halted = False
            enroll.save()
            
        return redirect('/admin-dash')
    
    # Logic: Generate and Send Receipt
    if request.GET.get('generate_receipt') == 'true':
        eid = request.GET.get('eid')
        enroll = Enrollment.objects.get(id=eid)
        
        due_amount = enroll.total_fee - enroll.amount_paid
    
        # Check if payment is partial or full to set the receipt message
        # --- Corrected Logic in admin_dashboard ---
        if enroll.amount_paid < enroll.total_fee:
    # Added the 'f' prefix to the string to enable variable interpolation
            msg = f"Partial Payment Received. Full payment still pending... classes may be put to halt until full payment. Remaining amount to be paid: ₹{due_amount}."
            messages.warning(request, f"Partial Receipt pushed. Due: ₹{due_amount} for {enroll.student.name}.")
        else:
            # Full payment logic
            enroll.is_halted = False
            msg = "Full Payment Received. Thank you!"
            messages.success(request, f"Full Receipt pushed for {enroll.student.name}.")
    
        enroll.save()

        OfficialReceipt.objects.create(
            enrollment=enroll,
            receipt_number=f"REC-{uuid.uuid4().hex[:6].upper()}",
            amount_verified=enroll.amount_paid,
            message=msg
        )
        
        return redirect('/admin-dash')
    
    # 3. Create the receipt in the database
        OfficialReceipt.objects.create(
            enrollment=enroll,
            receipt_number=f"REC-{uuid.uuid4().hex[:6].upper()}",
            amount_verified=enroll.amount_paid,
            message=msg
        )
        return redirect('/admin-dash')
    # --- DATA RETRIEVAL SECTION: Fetches context for the UI ---

    enrollments = Enrollment.objects.all()
    pending_teachers = Teacher.objects.filter(is_active=False)
    active_teachers = Teacher.objects.filter(is_active=True)
    all_courses = Course.objects.all()
    active_batches = Batch.objects.filter(is_completed=False)
    
    # Financial Reporting Logic
    total_revenue = enrollments.aggregate(Sum('amount_paid'))['amount_paid__sum'] or 0
    
    total_dues = enrollments.annotate(
        due=F('total_fee') - F('amount_paid')
    ).aggregate(Sum('due'))['due__sum'] or 0
    
    # Render the Dashboard
    return render(request, 'admin_dash.html', {
        'revenue': total_revenue,
        'dues': total_dues,
        'enrollments': enrollments,
        'batches': active_batches,
        'pending_teachers': pending_teachers,
        'active_teachers': active_teachers,
        'all_courses': all_courses
    })
# --- Teacher Portal ---
def teacher_portal(request):
    # 1. Security: Only allow teachers or superadmins
    if request.session.get('role') not in ['teacher', 'superadmin']:
        return redirect('/login')
    
    teacher_id = request.session.get('user_id')

    # --- ACTION LOGIC SECTION (Only for Active Batches) ---

    # Logic: Mark Attendance (Today's Date)
    # Updated Logic: Mark Attendance (Present or Absent)
    # Logic: Mark Attendance (Updated for Present and Absent)
    if request.GET.get('mark_attendance') == 'true':
        eid = request.GET.get('eid')
        status = request.GET.get('status')  # Captures 'present' or 'absent'
    
        # Determine the boolean value based on the status parameter
        is_present_val = (status == 'present')
    
        Attendance.objects.update_or_create(
            enrollment_id=eid,
            date=datetime.date.today(),
            defaults={'is_present': is_present_val}
        )
        return redirect('/teacher-portal?active=attendance')
    
    # Logic: Update Live Class Meeting Link
    if request.GET.get('update_link') == 'true':
        bid = request.GET.get('batch_id')
        new_link = request.GET.get('new_link')
        # Restriction: Only update links for non-completed batches
        Batch.objects.filter(id=bid, teacher_id=teacher_id, is_completed=False).update(class_link=new_link)
        return redirect('/teacher-portal')

    # Logic: Upload PDF Notes or Video Links
    if request.method == 'POST' and 'upload_resource' in request.POST:
        Resource.objects.create(
            batch_id=request.POST.get('batch_id'),
            title=request.POST.get('title'),
            notes=request.FILES.get('notes'),
            video_file=request.FILES.get('v_file'),
            video_url=request.POST.get('video_url')
        )
        return redirect('/teacher-portal')
    
    # Logic: Delete Resource
    if request.GET.get('delete_resource') == 'true':
        res_id = request.GET.get('res_id')
        Resource.objects.filter(id=res_id, batch__teacher_id=teacher_id).delete()
        return redirect('/teacher-portal?active=resources')

    # Logic: Save Assignment Feedback (POST)
    if request.method == 'POST' and 'submit_review' in request.POST:
        sub_id = request.POST.get('submission_id')
        AssignmentSubmission.objects.filter(id=sub_id).update(
            remarks=request.POST.get('remarks'),
            rating=request.POST.get('rating')
        )
        return redirect('/teacher-portal?active=grading')
    
    # Logic: Teacher Uploading Assignment Task
    if 'upload_task' in request.POST:
        Resource.objects.create(
            batch_id=request.POST.get('batch_id'),
            title="ASSIGNMENT: " + request.POST.get('title'),
            notes=request.FILES.get('task_file'),
        )
        return redirect('/teacher-portal?active=grading')
    
    # Logic: Delete Assignment Task
    if request.GET.get('delete_task') == 'true':
        task_id = request.GET.get('task_id')
        Resource.objects.filter(id=task_id, batch__teacher_id=teacher_id).delete()
        return redirect('/teacher-portal?active=grading')
    
    if request.GET.get('request_completion') == 'true':
        bid = request.GET.get('bid')
        # Mark the batch as ready for admin review in the Batch model
        Batch.objects.filter(id=bid, teacher_id=teacher_id).update(completion_requested=True)
        return redirect('/teacher-portal')
    
    # Logic: Reply to Student Doubt (Add this near your other POST logics)
    if request.method == 'POST' and 'reply_doubt' in request.POST:
        did = request.POST.get('doubt_id')
        DoubtReply.objects.create(
            doubt_id=did,
            replied_by_role='teacher',
            replied_by_name=request.session.get('name'),
            message=request.POST.get('reply_message')
        )
    # Auto-resolve the doubt so it clears from the active list
        StudentDoubt.objects.filter(id=did).update(is_resolved=True)
        return redirect('/teacher-portal?active=doubts')

    # --- DATA RETRIEVAL SECTION ---

    # --- DATA RETRIEVAL SECTION ---

    # 1. Active Batches: This removes them from Attendance and Resources tabs
    active_batches = Batch.objects.filter(
        teacher_id=teacher_id, 
        is_completed=False
    ).prefetch_related('enrollment_set__student').select_related('course')
    
    # 2. ADD THIS: Attendance Dictionary for Status Badges
    # Fetches today's records to show "Marked" status in the template
    marked_today = Attendance.objects.filter(
        date=datetime.date.today(),
        enrollment__batch__teacher_id=teacher_id
    ).values_list('enrollment_id', 'is_present')
    
    attendance_dict = {item[0]: item[1] for item in marked_today}

    # 2. Completed Batches: Archived view strictly for ratings/feedback
    completed_batches = Batch.objects.filter(
        teacher_id=teacher_id, 
        is_completed=True
    ).select_related('course').prefetch_related('enrollment_set__student')

    # 3. Grading Submissions: Filtered to "disappear" for finished courses
    submissions = AssignmentSubmission.objects.filter(
        batch__teacher_id=teacher_id,
        batch__is_completed=False # NEW: This clears the grading list for archived batches
    ).select_related('enrollment__student', 'enrollment__course', 'batch').order_by('-submitted_at')
    
    # 4. Student Doubts: Fetch unresolved questions for this teacher's batches
    doubts = StudentDoubt.objects.filter(
        batch__teacher_id=teacher_id,
        is_resolved=False # Only show pending questions
    ).select_related('enrollment__student', 'batch')

    return render(request, 'teacher_portal.html', {
        'batches': active_batches,
        'completed_batches': completed_batches,
        'submissions': submissions,
        'doubts': doubts,
        'attendance_dict': attendance_dict,
        'active_tab': request.GET.get('active', 'schedule')
    })

    # # --- DATA RETRIEVAL SECTION ---

    # # Fetch active batches specifically assigned to this teacher
    # # This also allows access to b.enrollment_set.all and b.resource_set.all in the template
    # my_batches = Batch.objects.filter(teacher_id=teacher_id, is_completed=False)
    
    # # Send today's date so the Attendance tab can display it
    # today_date = datetime.date.today() 

    # return render(request, 'teacher_portal.html', {
    #     'batches': my_batches,
    #     'today': today_date
    # })
# --- Student Course Logic ---

def courses(request):
    if not request.session.get('role'):
        return redirect('/login')

    student_id = request.session.get('user_id')
    
    # Handle course application logic
    if request.GET.get('apply'):
        c_id = request.GET.get('course_id')
        course_obj = Course.objects.get(id=c_id)
        
        # Create a pending enrollment record
        Enrollment.objects.create(
            student_id=student_id,
            course_id=c_id,
            total_fee=course_obj.fee,
            is_approved=False
        )
        return HttpResponse("Application submitted. Admin will generate your fees soon.")

    # CHANGE 1: Fetch all courses for the application section
    all_courses = Course.objects.all()

    # CHANGE 2: Fetch specific enrollments for the logged-in student
    # This allows the template to loop through enrolled batches
    user_enrollments = Enrollment.objects.filter(student_id=student_id)
        
    return render(request, 'courses.html', {
        'courses': all_courses, 
        'enrollments': user_enrollments  # Passing the enrollment list to HTML
    })
# --- Legacy Info Pages (Restricted by Role/Privilege) ---

def aboutus(request):
    data = aboutinfo.objects.first() #
    role = request.session.get('role')
    privs = request.session.get('priv', '')
    can_edit = role == 'superadmin' or 'about' in privs #
    
    if request.GET.get('update') == 'true' and can_edit:
        data.origin = request.GET.get('origin')
        data.mission = request.GET.get('mission')
        data.vision = request.GET.get('vision')
        data.save()
        return redirect('/aboutus')
    return render(request, 'aboutus.html', {'data': data, 'can_edit': can_edit})

def contactus(request):
    data = contactinfo.objects.first() #
    role = request.session.get('role')
    privs = request.session.get('priv', '')
    can_edit = role == 'superadmin' or 'contact' in privs #
    
    if request.GET.get('update') == 'true' and can_edit:
        data.address = request.GET.get('address')
        data.phone = request.GET.get('phone')
        data.email = request.GET.get('email')
        data.save()
        return redirect('/contactus')
    return render(request, 'contactus.html', {'data': data, 'can_edit': can_edit})

# Add this to app/views.py
def register(request):
    # Default to teacher registration
    reg_type = request.GET.get('type', 'teacher')
    
    if request.GET.get('submit') == 'true':
        role = request.GET.get('role')
        name = request.GET.get('name')
        email = request.GET.get('email')
        password = request.GET.get('password')

        if role == "teacher":
            # IMPORTANT: is_active=False prevents login until Admin approves
            Teacher.objects.create(
                name=name, 
                email=email, 
                password=password, 
                is_active=False
            )
            return HttpResponse("Teacher registration submitted! You can log in once an Admin approves your account.")
        
        return HttpResponse("Unauthorized registration type.")
        
    return render(request, 'register.html', {'reg_type': reg_type})
def student_manager(request):
    if request.session.get('role') not in ['admin', 'superadmin']:
        return redirect('/login')

    # Handle Student Creation
    if request.GET.get('create_student') == 'true':
        s_name = request.GET.get('s_name')
        s_email = request.GET.get('s_email')
        s_pass = request.GET.get('s_pass')
        try:
            student.objects.create(name=s_name, email=s_email, pwd=s_pass)
            return redirect('/student-manager')
        except IntegrityError:
            return HttpResponse("Error: A student with this email already exists.")

    # Handle Student Deletion
    if request.GET.get('delete_student') == 'true':
        sid = request.GET.get('sid')
        student.objects.filter(id=sid).delete()
        return redirect('/student-manager')

    all_students = student.objects.all()
    return render(request, 'student_manager.html', {'students': all_students})


def course_manager(request):
    # Security: Restrict to Admin/Superadmin only
    if request.session.get('role') not in ['admin', 'superadmin']:
        return redirect('/login')

    # Logic: Add New Course with Subject Code and Free Tier Toggle
    if request.GET.get('add_course') == 'true':
        title = request.GET.get('title')
        code = request.GET.get('subject_code')  
        desc = request.GET.get('desc')
        # Check if the course is marked as free
        is_free = request.GET.get('is_free') == 'true'
        # If free, set fee to 0; otherwise, capture the provided fee
        fee = 0 if is_free else request.GET.get('fee')
        
        Course.objects.create(
            title=title, 
            subject_code=code, 
            description=desc, 
            fee=fee,
            is_free=is_free # NEW: Save the free status to the database
        )
        return redirect('/course-manager')

    # Logic: Delete Course
    if request.GET.get('delete_course') == 'true':
        cid = request.GET.get('cid')
        Course.objects.filter(id=cid).delete()
        return redirect('/course-manager')

    all_courses = Course.objects.all()
    return render(request, 'course_manager.html', {'courses': all_courses})

def upload_payment_receipt(request):
    if request.session.get('role') != 'student':
        return redirect('/login')

    if request.method == 'POST':
        eid = request.POST.get('enrollment_id')
        receipt_file = request.FILES.get('receipt_file') # Captures the file
        
        enroll = Enrollment.objects.get(id=eid, student_id=request.session.get('user_id'))
        enroll.receipt = receipt_file
        # Update status to alert admin
        enroll.status = "Under Review" 
        enroll.save()
        
    return redirect('/courses')


from django.http import HttpResponse
from .models import Enrollment

from reportlab.lib import colors
from .models import Enrollment

import io
import qrcode # New import for QR generation
from django.http import FileResponse
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from .models import Enrollment

from reportlab.lib.utils import ImageReader
from .models import Enrollment

def download_certificate(request, eid):
    enroll = Enrollment.objects.get(id=eid)
    
    # SECURITY GUARD: Block if status is not 'Completed'
    if enroll.status != "Completed":
        return HttpResponse("Unauthorized: You did not complete this course successfully.", status=403)
    
    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=landscape(A4))
    width, height = landscape(A4)

    # 1. DRAW GRADIENT BACKGROUND (Gold -> White -> Gold)
    steps = 100
    for i in range(steps):
        ratio = i / (steps/2) if i < steps/2 else (steps - i) / (steps/2)
        p.setFillColorRGB(1.0, 0.84 + (0.16 * ratio), 0.0 + (1.0 * ratio))
        p.rect(i * (width/steps), 0, (width/steps) + 1, height, stroke=0, fill=1)

    # 2. GENERATE QR CODE
    verify_url = f"http://localhost:8000/verify-cert/{enroll.id}"
    qr = qrcode.QRCode(version=1, box_size=10, border=2)
    qr.add_data(verify_url)
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color="black", back_color="transparent")
    qr_buffer = io.BytesIO()
    qr_img.save(qr_buffer)
    qr_buffer.seek(0)

    # 3. INSTITUTE NAME & HEADER
    p.setFillColor(colors.darkblue)
    p.setFont("Helvetica-Bold", 40)
    p.drawCentredString(width/2, height-80, "TECH SYSTEM") # Institute Name
    
    p.setFillColor(colors.black)
    p.setFont("Helvetica-Bold", 28)
    p.drawCentredString(width/2, height-130, "CERTIFICATE OF COMPLETION")

    # 4. STUDENT DETAILS
    p.setFont("Times-Italic", 20)
    p.drawCentredString(width/2, height-180, "This is to certify that")
    
    p.setFont("Helvetica-Bold", 32)
    p.drawCentredString(width/2, height-230, enroll.student.name.upper())

    # 5. COURSE DETAILS
    p.setFont("Times-Italic", 18)
    p.drawCentredString(width/2, height-270, "has successfully completed the professional course in")
    
    p.setFont("Helvetica-Bold", 24)
    p.drawCentredString(width/2, height-310, enroll.course.title)
    
    # Detailed Course Description
    p.setFont("Helvetica-Oblique", 11)
    p.drawCentredString(width/2, height-340, f"Module Coverage: {enroll.course.description[:120]}...")

    # 6. QR CODE PLACEMENT
    p.drawImage(ImageReader(qr_buffer), 60, 60, width=80, height=80, mask='auto')
    p.setFont("Helvetica", 8)
    p.drawString(65, 50, "Scan to Verify Digital ID")

    # 7. DATE & AUTHORIZED SIGNATURE
    # Date of Completion
    completion_date = datetime.date.today().strftime("%B %d, %Y")
    p.setFont("Helvetica-Bold", 12)
    p.drawString(width-250, 160, f"Date: {completion_date}")
    
    # Signature for Director T.P. Agarwal
    p.setFont("Times-Italic", 15)
    p.drawRightString(width-80, 80, "T.P. Agarwal")
    p.setFont("Helvetica-Bold", 12)
    p.drawRightString(width-80, 65, "Director")
    # p.line(width-250, 85, width-80, 85)

    p.showPage()
    p.save()
    buffer.seek(0)
    return FileResponse(buffer, as_attachment=True, filename=f"Certificate_{enroll.student.name}.pdf")

def upload_assignment(request):
    # Security: Ensure only students can upload
    if request.session.get('role') != 'student':
        return redirect('/login')
    
    # Logic: Delete Submission
    if request.GET.get('delete_id'):
        sub_id = request.GET.get('delete_id')
        # Filter by enrollment student to ensure they own the submission
        AssignmentSubmission.objects.filter(
            id=sub_id, 
            enrollment__student_id=request.session.get('user_id')
        ).delete()
        return redirect('/courses')

    if request.method == 'POST':
        enrollment_id = request.POST.get('enrollment_id')
        file = request.FILES.get('assignment_file')
        
        # Verify student owns this enrollment
        try:
            enrollment = Enrollment.objects.get(
                id=enrollment_id, 
                student_id=request.session.get('user_id')
            )
            
            AssignmentSubmission.objects.create(
                enrollment=enrollment,
                batch=enrollment.batch,
                file=file
            )
        except Enrollment.DoesNotExist:
            pass # Handle error appropriately
            
        return redirect('/courses')
    
from django.db.models import Count, Q
from django.shortcuts import render, redirect
from .models import Enrollment, Course

def student_courses(request):
    # 1. Security: Only allow students
    if request.session.get('role') != 'student':
        return redirect('/login')
    
    user_id = request.session.get('user_id')
    
    # --- POST LOGIC: Process Review Submissions FIRST ---
    if request.method == "POST" and request.POST.get('submit_course_review'):
        enroll_id = request.POST.get('enrollment_id')
        rating = request.POST.get('rating')
        feedback = request.POST.get('feedback')

    # Update only if the enrollment exists for THIS student
        updated_rows = Enrollment.objects.filter(
            id=enroll_id, 
            student_id=user_id
        ).update(
            course_rating=int(rating),
            course_feedback=feedback
        )
    
        if updated_rows > 0:
            print(f"✅ Success: Rating linked for Enrollment {enroll_id}")
        else:
            print(f"❌ Error: Could not link rating for Enrollment {enroll_id}")

        return redirect('/courses')

    # --- GET LOGIC: Application Logic ---
    if request.GET.get('apply'):
        cid = request.GET.get('course_id')
        course = Course.objects.get(id=cid)
        
        # Logic to handle free vs paid enrollments
        is_free_val = course.is_free
        Enrollment.objects.create(
            student_id=user_id,
            course=course,
            is_approved=is_free_val,
            total_fee=0 if is_free_val else course.fee,
            status="Ongoing" if is_free_val else "Pending Approval"
        )
        return redirect('/courses')

    # --- DATA RETRIEVAL: Fetching updated data for the UI ---
    my_enrollments = Enrollment.objects.filter(
        student_id=user_id
    ).select_related('batch', 'course').prefetch_related(
        'officialreceipt_set', 
        'assignmentsubmission_set' 
    ).annotate(
        # Calculate balance and attendance on the fly
        remaining_balance=F('total_fee') - F('amount_paid'),
        present_days=Count('attendance', filter=Q(attendance__is_present=True))
    )

    return render(request, 'courses.html', {'enrollments': my_enrollments})
    
def update_enrollment(request):
    # We use GET here because your HTML form is using method="GET"
    eid = request.GET.get('eid')
    paid = request.GET.get('amt') 
    status = request.GET.get('status')
    
    if eid:
        enrollment = Enrollment.objects.get(id=eid)
        enrollment.amount_paid = paid # Match your model field name
        enrollment.status = status
        enrollment.save()
        
    return redirect('/admin-dash')

def verify_certificate(request, eid):
    try:
        # Fetch the enrollment record
        enroll = Enrollment.objects.get(id=eid)
        
        # A certificate is valid only if completed and approved
        is_valid = enroll.status == "Completed" and enroll.is_approved
        
        return render(request, 'verify_cert.html', {
            'enroll': enroll,
            'is_valid': is_valid,
            'date': datetime.date.today()
        })
    except Enrollment.DoesNotExist:
        # If ID doesn't exist, it's a fake certificate
        return render(request, 'verify_cert.html', {'is_valid': False})
    
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import inch
from django.http import FileResponse
import io

def download_receipt(request, rid):
    try:
        receipt = OfficialReceipt.objects.get(id=rid)
        enroll = receipt.enrollment
        role = request.session.get('role') # Get user role from session
    
        # Define the missing variable
        due_amount = enroll.total_fee - enroll.amount_paid
        
        # Updated Backend Guard: Allow Admin/Teacher to see it regardless of payment
        # Students are still blocked unless fully paid
        if role not in ['admin', 'superadmin', 'teacher']:
            if enroll.amount_paid < enroll.total_fee:
                return HttpResponse("Unauthorized. Complete payment to download official documents.", status=403)
        
        buffer = io.BytesIO()
        p = canvas.Canvas(buffer, pagesize=A4)
        width, height = A4

        # Layout Design
        p.setFont("Helvetica-Bold", 24)
        p.drawCentredString(width/2, height-1*inch, "TECH SYSTEM - PAYMENT RECEIPT")
        p.setFont("Helvetica", 10)
        p.drawCentredString(width/2, height-1.2*inch, "Official Billing Department")
        
        # Receipt Details
        p.line(1*inch, height-1.5*inch, width-1*inch, height-1.5*inch)
        p.setFont("Helvetica-Bold", 12)
        p.drawString(1*inch, height-2*inch, f"Receipt No: {receipt.receipt_number}")
        p.drawString(width-3*inch, height-2*inch, f"Date: {receipt.payment_date}")

        # Student & Course Info
        p.setFont("Helvetica", 12)
        p.drawString(1*inch, height-2.5*inch, f"Student Name: {enroll.student.name}")
        p.drawString(1*inch, height-2.8*inch, f"Course: {enroll.course.title}")
        p.drawString(1*inch, height-3.1*inch, f"Batch: {enroll.batch.batch_number}")

        # Financial Table
        p.rect(1*inch, height-5*inch, width-2*inch, 1.5*inch)
        p.line(1*inch, height-3.8*inch, width-1*inch, height-3.8*inch)
        p.drawString(1.2*inch, height-3.7*inch, "Description")
        p.drawRightString(width-1.2*inch, height-3.7*inch, "Amount (Rs.)")
        
        p.drawString(1.2*inch, height-4.2*inch, "Total Course Fee")
        p.drawRightString(width-1.2*inch, height-4.2*inch, f"{enroll.total_fee}")
        
        p.setFont("Helvetica-Bold", 12)
        p.drawString(1.2*inch, height-4.6*inch, "Amount Paid (Verified)")
        p.drawRightString(width-1.2*inch, height-4.6*inch, f"{receipt.amount_verified}")

        # Summary
        p.setFont("Helvetica-Bold", 14)
        p.drawRightString(width-1.2*inch, height-5.5*inch, f"Balance Due: Rs.{due_amount}")
        p.setFont("Helvetica-Oblique", 10)
        p.drawString(1*inch, height-6*inch, f"Status: {receipt.message}")

        p.showPage()
        p.save()
        buffer.seek(0)
        return FileResponse(buffer, as_attachment=True, filename=f"Receipt_{receipt.receipt_number}.pdf")

    except OfficialReceipt.DoesNotExist:
        return HttpResponse("Receipt not found.", status=404)
    
def mark_attendance(request):
    eid = request.GET.get('eid')
    enroll = Enrollment.objects.get(id=eid)
    
    # Ensure a record for 'today' is created
    Attendance.objects.get_or_create(
        enrollment=enroll,
        date=datetime.date.today(),
        defaults={'is_present': True}
    )
    return redirect('/teacher-portal')

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from .models import Enrollment, Attendance

def download_attendance_report(request, eid):
    try:
        # 1. Fetch data
        enroll = Enrollment.objects.get(id=eid)
        attendance_list = Attendance.objects.filter(
            enrollment=enroll, 
            is_present=True
        ).order_by('-date') # Show most recent first

        # 2. Setup PDF
        buffer = io.BytesIO()
        p = canvas.Canvas(buffer, pagesize=A4)
        width, height = A4

        # 3. Header
        p.setFont("Helvetica-Bold", 18)
        p.drawString(100, height - 80, f"Attendance Report: {enroll.course.title}")
        p.setFont("Helvetica", 12)
        p.drawString(100, height - 100, f"Student: {enroll.student.name}")
        p.drawString(100, height - 120, f"Batch: {enroll.batch.batch_number}")
        p.line(100, height - 130, 500, height - 130)

        # 4. List Dates
        y_position = height - 160
        p.setFont("Helvetica-Bold", 12)
        p.drawString(100, y_position, "Date")
        p.drawString(300, y_position, "Status")
        y_position -= 20
        p.setFont("Helvetica", 12)

        for record in attendance_list:
            if y_position < 50: # Handle page break
                p.showPage()
                y_position = height - 50
            
            p.drawString(100, y_position, str(record.date))
            p.drawString(300, y_position, "Present")
            y_position -= 20

        # 5. Summary
        p.line(100, y_position, 500, y_position)
        p.setFont("Helvetica-Bold", 12)
        p.drawString(100, y_position - 20, f"Total Days Present: {attendance_list.count()}")

        p.showPage()
        p.save()
        buffer.seek(0)
        return FileResponse(buffer, as_attachment=True, filename=f"Attendance_{enroll.batch.batch_number}.pdf")

    except Enrollment.DoesNotExist:
        return HttpResponse("Enrollment not found.", status=404)
    
from django.utils import timezone
from .models import Enrollment, OfficialReceipt

def generate_and_push_receipt(request):
    eid = request.GET.get('eid')
    try:
        enroll = Enrollment.objects.get(id=eid)
        
        # 1. DELETE PREVIOUS RECEIPTS
        # This ensures only the newest receipt exists for this enrollment
        OfficialReceipt.objects.filter(enrollment=enroll).delete()
        
        # 2. CREATE THE NEW RECEIPT
        # payment_date is handled automatically by auto_now_add=True
        OfficialReceipt.objects.create(
            enrollment=enroll,
            receipt_number=f"REC-{enroll.id}-{timezone.now().strftime('%S%M%H')}",
            amount_verified=enroll.amount_paid,
            message=f"Latest receipt updated for verified amount of ₹{enroll.amount_paid}"
        )
        
    except Enrollment.DoesNotExist:
        pass # Handle error as needed
        
    return redirect('/admin-dash')


from django.shortcuts import redirect
from .models import Course, Enrollment, Batch

def apply_course(request):
    if request.method == "GET" and request.GET.get('apply'):
        course_id = request.GET.get('course_id')
        student_id = request.session.get('user_id')
        course = Course.objects.get(id=course_id)
        
        # Check if course is free
        if course.is_free:
            # Auto-approve for free courses
            # You might want to assign a default 'Free Tier' batch here
            default_batch = Batch.objects.filter(course=course).first() 
            
            Enrollment.objects.create(
                student_id=student_id,
                course=course,
                batch=default_batch,
                is_approved=True,  # Automated access
                total_fee=0,
                amount_paid=0,
                status="Ongoing"
            )
        else:
            # Standard process for paid courses: needs Admin approval
            Enrollment.objects.create(
                student_id=student_id,
                course=course,
                is_approved=False, # Wait for Admin
                total_fee=course.fee,
                amount_paid=0,
                status="Under Review"
            )
            
        return redirect('/courses')
    
def create_course(request):
    if request.method == "POST":
        title = request.POST.get('title')
        description = request.POST.get('description')
        fee = request.POST.get('fee')
        # If the checkbox is checked, it returns 'on', otherwise None
        is_free = request.POST.get('is_free') == 'on' 

        Course.objects.create(
            title=title,
            description=description,
            fee=0 if is_free else fee, # Set fee to 0 if free
            is_free=is_free
        )
        return redirect('/course-manager')
    

# New view for the separate Explore page
def explore_courses(request):
    if request.session.get('role') != 'student':
        return redirect('/login')
        
    user_id = request.session.get('user_id')
    
    # Logic for Search
    query = request.GET.get('search', '')
    if query:
        courses = Course.objects.filter(title__icontains=query)
    else:
        courses = Course.objects.all()

    # Logic for applying to a course
    if request.GET.get('apply'):
        cid = request.GET.get('course_id')
        course = Course.objects.get(id=cid)
        
        if course.is_free:
            Enrollment.objects.create(
                student_id=user_id, course=course, is_approved=True, 
                total_fee=0, status="Ongoing"
            )
        else:
            Enrollment.objects.create(
                student_id=user_id, course=course, is_approved=False, 
                total_fee=course.fee, status="Pending Approval"
            )
        return redirect('/courses') # Redirect to dashboard after applying

    return render(request, 'explore.html', {'courses': courses, 'query': query})

# Updated dashboard view (Removed 'all_courses' logic)
def student_courses(request):
    if request.session.get('role') != 'student':
        return redirect('/login')
    
    user_id = request.session.get('user_id')
    
    # CRITICAL: Use the model name + _set to prefetch
    my_enrollments = Enrollment.objects.filter(
        student_id=user_id
    ).select_related('batch', 'course').prefetch_related(
        'officialreceipt_set', 
        'assignmentsubmission_set' 
    ).annotate(
        present_days=Count('attendance', filter=Q(attendance__is_present=True))
    )

    return render(request, 'courses.html', {'enrollments': my_enrollments})
def student_manager_list(request):
    # Security: Only allow admins
    if request.session.get('role') != 'superadmin' and 'student' not in request.session.get('priv', []):
        return redirect('/login')

    # Fetch approved enrollments with related data for performance
    active_students = Enrollment.objects.filter(
        is_approved=True
    ).select_related('student', 'course', 'batch').order_by('-id')

    return render(request, 'student_manager_list.html', {
        'active_students': active_students
    })
    
    
def review_assignments(request):
    # Security: Allow admin or teacher
    if request.session.get('role') not in ['admin', 'superadmin', 'teacher']:
        return redirect('/login')

    # Handle the rating submission
    if request.method == "POST" and request.POST.get('submit_rating'):
        assignment_id = request.POST.get('assignment_id')
        rating = request.POST.get('rating')
        feedback = request.POST.get('feedback')
        
        # Assuming you have an Assignment model linked to Enrollment
        assignment = Assignment.objects.get(id=assignment_id)
        assignment.rating = rating
        assignment.feedback = feedback
        assignment.status = "Reviewed"
        assignment.save()
        return redirect('/review-assignments')

    # Fetch assignments (adjust model names as per your schema)
    pending_assignments = Assignment.objects.filter(status="Pending").select_related('enrollment__student', 'enrollment__course')
    
    return render(request, 'review_assignments.html', {'assignments': pending_assignments})

def teacher_review_assignments(request):
    # Security: Only allow users with teacher or admin roles
    if request.session.get('role') not in ['teacher', 'admin', 'superadmin']:
        return redirect('/login')

    if request.method == "POST":
        submission_id = request.POST.get('submission_id')
        rating = request.POST.get('rating')
        remarks = request.POST.get('remarks')
        
        # Update the specific submission with feedback
        submission = AssignmentSubmission.objects.get(id=submission_id)
        submission.rating = rating
        submission.remarks = remarks
        submission.save()
        return redirect('/teacher-review')

    # Fetch submissions for the batches assigned to this teacher
    # Adjust filtering based on how you link teachers to batches
    submissions = AssignmentSubmission.objects.all().select_related('enrollment__student', 'enrollment__course', 'batch')
    
    return render(request, 'teacher_review.html', {'submissions': submissions})

def submit_course_review(request):
    """
    Dedicated view to process course ratings and feedback.
    Links the submission strictly to the logged-in student's enrollment.
    """
    # 1. Security: Check role and session
    if request.session.get('role') != 'student':
        return redirect('/login')

    if request.method == "POST":
        user_id = request.session.get('user_id')
        enroll_id = request.POST.get('enrollment_id')
        rating_val = request.POST.get('rating')
        feedback_text = request.POST.get('feedback')

        try:
            # 2. Relationship Link: Find the enrollment belonging to this student
            # This ensures the rating is saved to the correct 'student' record
            enrollment = Enrollment.objects.get(id=enroll_id, student_id=user_id)
            
            # 3. Save the Data
            enrollment.course_rating = int(rating_val)
            enrollment.course_feedback = feedback_text
            enrollment.save()
            
            print(f"✅ Review saved for student {user_id} on enrollment {enroll_id}")
            
        except (Enrollment.DoesNotExist, ValueError, TypeError) as e:
            print(f"❌ Review Save Failed: {e}")
            
    # Redirect back to the dashboard to show the 'Thank You' message
    return redirect('/courses')

def batch_manager(request):
    # 1. Security: Only Superadmin
    if request.session.get('role') != 'superadmin':
        return redirect('/login')

    # --- LOGIC: Create Batch (POST) stays as is ---
    if request.method == "POST" and request.POST.get('create_batch'):
        # ... (keep existing create logic) ...
        return redirect('/batch-manager')

    # --- UPDATED LOGIC: Finish Batch (GET) ---
    # Replace your old 'finish_batch' block with this:
    if request.GET.get('finish_batch') == 'true':
        bid = request.GET.get('bid')
        batch = Batch.objects.get(id=bid)
        
        # 1. Mark the batch as officially completed
        # This removes it from the teacher's active list and student's active schedule
        batch.is_completed = True
        batch.save()
        
        # 2. Update Enrollment Status
        # IMPORTANT: Access is blocked and certificate is NOT generated 
        # UNLESS the status is explicitly set to "Completed"
        # Enrollment.objects.filter(batch=batch).update(status="Completed")
        
        print(f"🔒 Batch {batch.batch_number} Archived. Access blocked for incomplete students.")
        return redirect('/batch-manager')

    # --- DATA RETRIEVAL ---
    # Filter for batches where a teacher has sent a request
    completion_requests = Batch.objects.filter(
        completion_requested=True, 
        is_completed=False
    ).select_related('course', 'teacher')

    # Filter for standard active batches (no request sent yet)
    active_batches = Batch.objects.filter(
        is_completed=False, 
        completion_requested=False
    ).select_related('course', 'teacher')

    return render(request, 'batch_manager.html', {
        'completion_requests': completion_requests,
        'active_batches': active_batches,
        'courses': Course.objects.all(),
        'teachers': Teacher.objects.filter(is_active=True)
    })
    
from django.http import HttpResponse
from .models import Enrollment, Attendance, AssignmentSubmission

import io
from django.http import HttpResponse
from reportlab.lib import colors
from reportlab.platypus import Paragraph, Spacer, Table, TableStyle, SimpleDocTemplate
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from .models import Enrollment, Attendance, AssignmentSubmission

def download_report_analysis(request, eid):
    # Fetch student enrollment details
    enroll = Enrollment.objects.get(id=eid)
    styles = getSampleStyleSheet()
    
    # --- DATA GATHERING ---
    
    # 1. Attendance Data Calculation
    all_class_dates = Attendance.objects.filter(
        enrollment__batch=enroll.batch
    ).values_list('date', flat=True).distinct().order_by('date')
    
    present_dates = Attendance.objects.filter(
        enrollment=enroll, 
        is_present=True
    ).values_list('date', flat=True)
    
    total_classes = all_class_dates.count()
    present_count = present_dates.count()
    attendance_pct = (present_count / total_classes * 100) if total_classes > 0 else 0

    # 2. Assignment Analytics
    submissions = AssignmentSubmission.objects.filter(enrollment=enroll).order_by('-submitted_at')
    valid_grades = [s.rating for s in submissions if s.rating is not None]
    avg_grade = sum(valid_grades) / len(valid_grades) if valid_grades else 0

    # 3. Final Result Logic
    # Requirements: 75% attendance and 5/10 average grade
    is_passed = attendance_pct >= 75 and avg_grade >= 5

    # --- PDF BUILDING ---
    
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    elements = []

    # Header & Branding
    elements.append(Paragraph(f"TECH SYSTEM - Performance Report", styles['Title']))
    elements.append(Paragraph(f"Student: {enroll.student.name} | Course: {enroll.course.title}", styles['Normal']))
    elements.append(Paragraph(f"Batch Number: {enroll.batch.batch_number}", styles['Normal']))
    elements.append(Spacer(1, 12))

    # 4. Attendance History Table
    elements.append(Paragraph("Detailed Attendance History", styles['Heading2']))
    att_data = [['Date', 'Status']]
    for d in all_class_dates:
        status = "Present" if d in present_dates else "Absent"
        att_data.append([d.strftime('%Y-%m-%d'), status])
    
    att_table = Table(att_data, colWidths=[120, 100])
    att_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.dodgerblue),
        ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('GRID', (0,0), (-1,-1), 1, colors.grey),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.whitesmoke, colors.lightgrey])
    ]))
    elements.append(att_table)
    elements.append(Spacer(1, 20))

    # 5. Assignment & Feedback Table
    elements.append(Paragraph("Assignment & Feedback Analytics", styles['Heading2']))
    grad_data = [['File Name', 'Grade', 'Teacher Remarks']]
    for s in submissions:
        # Extracts filename and displays rating
        filename = s.file.name.split('/')[-1] if s.file else "N/A"
        grade = f"{s.rating}/10" if s.rating is not None else "Pending"
        remarks = s.remarks if s.remarks else "No feedback yet"
        grad_data.append([filename, grade, remarks])
    
    grad_table = Table(grad_data, colWidths=[150, 60, 240])
    grad_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.forestgreen),
        ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
        ('GRID', (0,0), (-1,-1), 1, colors.grey),
        ('FONTSIZE', (0,1), (-1,-1), 9),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE')
    ]))
    elements.append(grad_table)

    # 6. Final Performance Summary
    elements.append(Spacer(1, 30))
    elements.append(Paragraph("Final Performance Summary", styles['Heading2']))
    
    summary_text = f"""
    <b>Total Attendance:</b> {attendance_pct:.1f}% ({present_count}/{total_classes} days)<br/>
    <b>Average Assignment Grade:</b> {avg_grade:.1f}/10<br/>
    <b>Final Result:</b> <font color="{'green' if is_passed else 'red'}">{'PASSED' if is_passed else 'FAILED'}</font>
    """
    elements.append(Paragraph(summary_text, styles['Normal']))

    # --- FINALIZING PDF ---
    
    # Build the document into the buffer
    doc.build(elements)
    
    # Seek to the start of the buffer to avoid "Failed to load PDF" error
    buffer.seek(0)
    
    # Create the HTTP response with correct content type
    response = HttpResponse(buffer, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="Report_{enroll.student.name}.pdf"'
    
    return response

from django.shortcuts import render, redirect
from .models import StudentDoubt, DoubtReply # Ensure these match your models

from django.shortcuts import render, redirect
from .models import StudentDoubt, Enrollment

from django.shortcuts import render, redirect, get_object_or_404
from .models import StudentDoubt, Enrollment

def student_doubts(request):
    student_id = request.session.get('user_id')
    if not student_id:
        return redirect('/login')

    # 1. Fetch user's enrollments for the dropdown
    my_enrollments = Enrollment.objects.filter(student_id=student_id, is_approved=True)

    # 2. Handle Resolve Action
    if request.GET.get('resolve_doubt') == 'true':
        did = request.GET.get('did')
        StudentDoubt.objects.filter(id=did, enrollment__student_id=student_id).update(is_resolved=True)
        return redirect('/courses?active=doubts') # Matches pattern #8/21

    # 3. Handle Form Submission
    if request.method == 'POST':
        # Retrieve name="enrollment_id" from select tag
        selected_eid = request.POST.get('enrollment_id')
        
        if selected_eid:
            # SECURITY FIX: Ensure the enrollment actually belongs to this student
            # This prevents manual ID tampering that causes "DoesNotExist" errors
            enroll_obj = get_object_or_404(Enrollment, id=selected_eid, student_id=student_id)
            
            StudentDoubt.objects.create(
                enrollment_id=selected_eid, 
                batch_id=enroll_obj.batch.id, # Link batch automatically
                title=request.POST.get('title'),
                description=request.POST.get('description'),
                screenshot=request.FILES.get('screenshot')
            )
            return redirect('/courses?active=doubts')
        
    # 4. Data Retrieval for History
    doubts = StudentDoubt.objects.filter(
        enrollment__student_id=student_id
    ).prefetch_related('replies').order_by('-created_at')
    
    return render(request, 'doubts.html', {
        'doubts': doubts,
        'my_enrollments': my_enrollments
    })