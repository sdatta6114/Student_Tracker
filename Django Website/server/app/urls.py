from django.urls import path
from . import views

urlpatterns = [
    # path('home', views.home),
    # path('aboutus', views.aboutus),
    # path('contactus', views.contactus),
    # path('login', views.login),
    # path('register', views.register),
    # path('logout', views.logout),
    # # path('superadmin-dash', views.superadmin_dash),
    # path('admin-dash', views.admin_dashboard),
    # path('teacher-portal', views.teacher_portal),
    # path('courses', views.courses),
    
    path('home', views.home),
    path('login', views.login),
    path('register', views.register),
    path('logout', views.logout),
    path('admin-dash', views.admin_dashboard), # Make sure this name matches views.py
    path('teacher-portal', views.teacher_portal),
    path('courses', views.courses),
    path('aboutus', views.aboutus),
    path('contactus', views.contactus),
    path('student-manager', views.student_manager),
    path('course-manager', views.course_manager),
    path('teacher-portal', views.teacher_portal, name='teacher_portal'),
    path('courses', views.student_courses, name='student_courses'),
    path('update-enrollment', views.update_enrollment, name='update_enrollment'),
    path('download-certificate/<int:eid>', views.download_certificate, name='download_certificate'),
    path('verify-cert/<int:eid>', views.verify_certificate, name='verify_certificate'),
    # path('download-certificate/<int:eid>', views.download_certificate, name='download_certificate'), # Fixes 404 for certificates
    path('download-receipt/<int:rid>', views.download_receipt, name='download_receipt'),             # Fixes 404 for receipts
    # path('verify-cert/<int:eid>', views.verify_certificate, name='verify_certificate'),    
    # Essential for QR verification
    path('download-attendance/<int:eid>', views.download_attendance_report, name='download_attendance'),
    path('generate-receipt/', views.generate_and_push_receipt, name='generate_and_push_receipt'),
    path('upload-assignment', views.upload_assignment, name='upload_assignment'),
    path('courses', views.student_courses, name='student_courses'),
    path('explore', views.explore_courses, name='explore_courses'),
    # ... your existing paths
    # path('student-manager-list', views.student_manager_list, name='student_manager_list'),
    # path('student-manager', views.student_manager_list, name='student_manager'),
    # path('student-manager', views.student_manager_list, name='student_manager_list'),
    path('teacher-review', views.teacher_review_assignments, name='teacher_review'),
    path('submit-review', views.submit_course_review, name='submit_review'),
    path('batch-manager', views.batch_manager, name='batch_manager'),
    path('download-report/<int:eid>/', views.download_report_analysis, name='download_report'),
    # FEATURE: Student Doubt Section
    # This handles the main list and submission form for students
    # Student dashboard link (Redirect target)
    path('courses', views.courses, name='student_courses'),
    path('doubts', views.student_doubts, name='student_doubts'),
    path('teacher-portal', views.teacher_portal, name='teacher_portal'),
]     # Pattern #28/30

