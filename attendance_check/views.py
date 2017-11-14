#-*- coding: utf-8 -*-
from django.shortcuts import render
from rest_framework_jwt.authentication import JSONWebTokenAuthentication
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.contrib.auth import authenticate
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.views import Response

from attendance_check.serializers import ( RegistrationSerializer,
                                           LectureCreateSerializer,
                                           LectureStartSerializer,
                                           LectureRequestAttendanceCheckSerializer,
                                           LectureReceiveApplySerializer,
                                           LectureListSerializer,
                                           ProfessorProfileSerializer,
                                           StudentProfileSerializer )

from django.utils import timezone
from .models import ( ProfessorProfile,
                      Lecture,
                      Department,
                      StudentProfile,
                      AttendanceRecord,
                      AttendanceCard,
                      LectureReceiveCard,
                      )

from django.contrib.auth.models import User
from django.contrib.auth.hashers import make_password

from django.utils import timezone
import datetime
# Create your views here.


def mainView(request):

    return render(request, 'attendance_check/main.html')

def loginView(request):

    return render(request, 'attendance_check/login.html')

def virtualClassView(request):

    return render(request, 'attendance_check/virtual_class.html')

class RegistrationView(APIView):
    permission_classes = (AllowAny,)
    authentication_classes = ()
    def get(self, request):
        return Response(status=status.HTTP_400_BAD_REQUEST)

    def put(self, request):
        serializer = RegistrationSerializer(data=request.data)
        if serializer.is_valid():
            newUser = User.objects.create(
                username=serializer.validated_data['username'],
                email=serializer.validated_data['email'],
                password=make_password(serializer.validated_data['password']),
                is_staff=serializer.validated_data['is_staff'],
            )
            newUser.save()
            if serializer.validated_data['is_staff']:
                newProf = ProfessorProfile.objects.create(
                    user=newUser,
                    employee_id=serializer.validated_data['id'],
                    department=Department.objects.get(pk=serializer.validated_data['department']),
                )
                newProf.save()

            else :
                newStudentProfile = StudentProfile.objects.create(
                    user=newUser,
                    student_id=serializer.validated_data['id'],
                    department=Department.objects.get(pk=serializer.validated_data['department']),
                )
                newStudentProfile.save()

            return Response(serializer.validated_data['department'])
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ProfileView(APIView):
    permission_classes = (IsAuthenticated,)
    authentication_classes = (JSONWebTokenAuthentication,)

    def get(self, request):

        if request.user.is_staff:
            prof = ProfessorProfile.objects.get(user=request.user)

            result = {
                'username' : request.user.username,
                'email' : request.user.email,
                'user_type' : u'교수',
                'id' : prof.employee_id,
                'department' : prof.department.name,
            }


            return Response(result)
        else:
            sdt = StudentProfile.objects.get(user=request.user)

            result = {
                'username' : request.user.username,
                'email' : request.user.email,
                'user_type' : u'학생',
                'id' : sdt.student_id,
                'department' : sdt.department.name,
            }

            return Response(result)


class LectureCreateView(APIView):
    permission_classes = (IsAuthenticated,)
    authentication_classes = (JSONWebTokenAuthentication,)

    def post(self, request):
        if not request.user.is_staff:
            return Response("Lecture only can created by staff user.", status=status.HTTP_403_FORBIDDEN)

        serializer = LectureCreateSerializer(data=request.data)

        if serializer.is_valid():
            professorProfile = ProfessorProfile.objects.get(user=request.user)

            lec = Lecture.objects.create(
                title=serializer.validated_data['title'],
                lecturer=professorProfile,
            )
            lec.save()

            return Response(serializer.data)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


    def get(self, request):
        return Response(status=status.HTTP_400_BAD_REQUEST)

class LectureListView(APIView):
    permission_classes = (IsAuthenticated,)
    authentication_classes = (JSONWebTokenAuthentication,)

    def get(self, request):

        if request.user.is_staff:
            prof = ProfessorProfile.objects.get(user=request.user)
            lecture_set = Lecture.objects.filter(lecturer=prof)

            lectures = []

            for lecture in lecture_set:
                lectures.append({
                    "id": lecture.pk,
                    "title": lecture.title
                })
            result = {"lectures": lectures}
            return Response(result)
        else:

            lectures = { "lectures" : Lecture.objects.values()}

            return Response(lectures)



class LectureStartView(APIView):
    permission_classes = (IsAuthenticated,)
    authentication_classes = (JSONWebTokenAuthentication,)

    def post(self, request):
        if not request.user.is_staff:
            return Response("Lecture only can started by staff user.", status=status.HTTP_403_FORBIDDEN)

        serializer = LectureStartSerializer(data=request.data)
        if serializer.is_valid():
            lecture = Lecture.objects.get(pk=serializer.validated_data['id'])
            record = AttendanceRecord.objects.create(
                activate = True,
                start_time = timezone.now(),
                end_time = timezone.now()  + datetime.timedelta(minutes = serializer.validated_data['minute']),
                lecture = lecture
            )

            record.save()

            return Response(serializer.data)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class LectureStopView(APIView):
    permission_classes = (IsAuthenticated,)
    authentication_classes = (JSONWebTokenAuthentication,)

    def post(self, request):
        if not request.user.is_staff:
            return Response("Lecture only can stopped by staff user.", status=status.HTTP_403_FORBIDDEN)

        serializer = LectureStartSerializer(data=request.data)
        if serializer.is_valid():
            lecture = Lecture.objects.get(pk=serializer.validated_data['id'])
            record = AttendanceRecord.objects.get(lecture=lecture)
            record.activate = False
            record.save()

            return Response(serializer.data)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LectureRequestAttendaneCheck(APIView):
    permission_classes = (IsAuthenticated,)
    authentication_classes = (JSONWebTokenAuthentication,)

    def post(self, request):
        serializer = LectureRequestAttendanceCheckSerializer(data=request.data)

        if request.user.is_staff:

            if serializer.is_valid():


                student = StudentProfile.objects.get(user=User.objects.get(pk=serializer.validated_data['user']))



                lecture = Lecture.objects.get(pk=serializer.validated_data['lecture'])

                is_received = LectureReceiveCard.objects.get(card_owner=student, target_lecture=lecture)

                if not is_received:
                    return Response("You are not received this Lecture.", status=status.HTTP_403_FORBIDDEN)

                record = lecture.attendancerecord_set.get(activate=True)

                if not record:
                    return Response("Not Exist Activate Lecture.", status=status.HTTP_403_FORBIDDEN)

                allow_seconds = ( record.start_time - record.end_time ).seconds

                is_late = False
                if  (record.end_time - timezone.now()).seconds < allow_seconds :
                    is_late = False
                else :
                    is_late = True

                override_check = AttendanceCard.objects.get(checker=student, record_to=record)
                if override_check:
                    return Response("Already checked in this Lecture.", status=status.HTTP_403_FORBIDDEN)

                card = AttendanceCard.objects.create(
                    check_time = datetime.datetime.now(),
                    checker = student,
                    record_to = record,
                    is_late_checker =  is_late
                )
                card.save()

                return Response(serializer.data)
            else:
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        else:

            if serializer.is_valid():

                student = StudentProfile.objects.get(user=request.user)

                lecture = Lecture.objects.get(pk=serializer.validated_data['lecture'])

                is_received = LectureReceiveCard.objects.filter(card_owner=student, target_lecture=lecture)

                if not is_received.exists():
                    return Response("You are not received this Lecture.", status=status.HTTP_403_FORBIDDEN)

                record_set = lecture.attendancerecord_set.filter(activate=True)

                if not record_set.exists():
                    return Response("Not Exist Activate Lecture.", status=status.HTTP_403_FORBIDDEN)

                record = record_set.first()
                allow_seconds = (record.start_time - record.end_time).seconds

                is_late = False
                if (record.end_time - timezone.now()).seconds < allow_seconds:
                    is_late = False
                else:
                    is_late = True

                override_check = AttendanceCard.objects.filter(checker=student, record_to=record)
                if override_check.exists():
                    return Response("Already checked in this Lecture.", status=status.HTTP_403_FORBIDDEN)

                card = AttendanceCard.objects.create(
                    check_time=datetime.datetime.now(),
                    checker=student,
                    record_to=record,
                    is_late_checker=is_late
                )
                card.save()

                return Response(serializer.data)
            else:
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class LectureRecordStatusView(APIView):
    permission_classes = (IsAuthenticated,)
    authentication_classes = (JSONWebTokenAuthentication,)

    def get(self, request):
        if request.user.is_staff:
            prof = ProfessorProfile.objects.get(user=request.user)
            lecture = Lecture.objects.get(lecturer=prof)
            record = AttendanceRecord.objects.get(activate=True, lecture=lecture)
            cards = record.attendancecard_set.values()

            return Response(cards)
        else:
            return Response("Lecture Record Status can read by staff user.", status=status.HTTP_403_FORBIDDEN)


class LectureReceiveApplyView(APIView):
    permission_classes = (IsAuthenticated,)
    authentication_classes = (JSONWebTokenAuthentication,)

    def post(self, request):
        if not request.user.is_staff:
            serializer = LectureReceiveApplySerializer(data = request.data)

            if serializer.is_valid():
                student = StudentProfile.objects.get(user=request.user)
                lecture = Lecture.objects.get(pk=serializer.validated_data['lecture'])
                receive_card = LectureReceiveCard.objects.create(
                    target_lecture = lecture,
                    card_owner = student
                )
                receive_card.save()
                return Response(serializer.data)
            else:
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response("Lecture Receive Apply can only student", status=status.HTTP_403_FORBIDDEN)

class LectureReceiveApplyListView(APIView):
    permission_classes = (IsAuthenticated,)
    authentication_classes = (JSONWebTokenAuthentication,)

    def post(self, request):
        if request.user.is_staff:
            serializer = LectureReceiveApplySerializer(data = request.data)
            if serializer.is_valid():
                lecture = Lecture.objects.get(pk=serializer.validated_data['lecture'])
                cards = LectureReceiveCard.objects.filter(target_lecture=lecture)

                student_infos = []
                for card in cards:
                    student_info = {
                        "student_id" : card.card_owner.student_id,
                        "id" : card.card_owner.pk
                    }
                    student_infos.append(student_info)

                result = {
                    "students" : student_infos
                }
                return Response(result)
            else:
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response("Lecture Receive Apply List only can read by student", status=status.HTTP_403_FORBIDDEN)


class DepartmentListView(APIView):
    permission_classes = (AllowAny,)
    authentication_classes = ()

    def get(self, request):
        departments = { "departments" : Department.objects.values() }


        return Response(departments)