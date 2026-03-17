from django.test import TestCase

# Create your tests here.
from datetime import date
from decimal import Decimal
from django.test import TestCase, Client
from django.urls import reverse
from django.db import IntegrityError

from .models import (
    User,
    DailyRecord,
    MoodRecord,
    SleepRecord,
    ExerciseRecord,
    WorkStudyRecord,
)


class UserModelTest(TestCase):
    def test_user_id_is_generated_automatically(self):
        user = User.objects.create(email='test1@example.com')
        self.assertIsNotNone(user.user_id)
        self.assertEqual(len(user.user_id), 6)
        self.assertTrue(user.user_id.isdigit())

    def test_set_password_and_check_password(self):
        user = User.objects.create(email='test2@example.com')
        user.set_password('mypassword123')

        self.assertNotEqual(user.password, 'mypassword123')
        self.assertTrue(user.check_password('mypassword123'))
        self.assertFalse(user.check_password('wrongpassword'))

    def test_user_str_returns_email(self):
        user = User.objects.create(email='test3@example.com')
        self.assertEqual(str(user), 'test3@example.com')


class DailyRecordModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create(email='daily@example.com')

    def test_create_daily_record(self):
        record = DailyRecord.objects.create(
            user=self.user,
            record_date=date(2026, 3, 17)
        )
        self.assertEqual(record.user, self.user)
        self.assertEqual(record.record_date, date(2026, 3, 17))

    def test_daily_record_unique_constraint_per_user_per_day(self):
        DailyRecord.objects.create(user=self.user, record_date=date(2026, 3, 17))

        with self.assertRaises(IntegrityError):
            DailyRecord.objects.create(user=self.user, record_date=date(2026, 3, 17))

    def test_daily_record_str(self):
        record = DailyRecord.objects.create(
            user=self.user,
            record_date=date(2026, 3, 17)
        )
        self.assertEqual(str(record), f"{self.user.user_id} - 2026-03-17")


class RelatedModelsTest(TestCase):
    def setUp(self):
        self.user = User.objects.create(email='related@example.com')
        self.daily_record = DailyRecord.objects.create(
            user=self.user,
            record_date=date(2026, 3, 17)
        )

    def test_create_mood_record(self):
        mood = MoodRecord.objects.create(
            daily_record=self.daily_record,
            mood_rating=4,
            stress_rating=3,
            anxiety_rating=5,
            note_text='Feeling okay today'
        )
        self.assertEqual(mood.daily_record, self.daily_record)
        self.assertEqual(mood.mood_rating, 4)
        self.assertEqual(mood.note_text, 'Feeling okay today')

    def test_create_sleep_record(self):
        sleep = SleepRecord.objects.create(
            daily_record=self.daily_record,
            status='complete',
            sleep_time='2026-03-16 23:00:00',
            wake_time='2026-03-17 07:00:00',
            sleep_duration=8.0
        )
        self.assertEqual(sleep.daily_record, self.daily_record)
        self.assertEqual(sleep.status, 'complete')

    def test_create_exercise_record(self):
        exercise = ExerciseRecord.objects.create(
            daily_record=self.daily_record,
            did_exercise=True,
            exercise_type='Running',
            exercise_duration=30
        )
        self.assertTrue(exercise.did_exercise)
        self.assertEqual(exercise.exercise_type, 'Running')
        self.assertEqual(exercise.exercise_duration, 30)

    def test_create_workstudy_record(self):
        workstudy = WorkStudyRecord.objects.create(
            daily_record=self.daily_record,
            workstudy_hours=Decimal('4.50')
        )
        self.assertEqual(workstudy.workstudy_hours, Decimal('4.50'))


class ViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create(email='viewtest@example.com')
        self.user.set_password('testpass123')

    def test_login_page_get(self):
        response = self.client.get(reverse('login'))
        self.assertEqual(response.status_code, 200)

    def test_login_success(self):
        response = self.client.post(reverse('login'), {
            'email': 'viewtest@example.com',
            'password': 'testpass123'
        })
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('home'))

    def test_login_wrong_password(self):
        response = self.client.post(reverse('login'), {
            'email': 'viewtest@example.com',
            'password': 'wrongpass'
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Password incorrect')

    def test_home_requires_login(self):
        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, 302)

    def test_home_after_login(self):
        session = self.client.session
        session['user_name'] = self.user.email
        session['user_id'] = self.user.user_id
        session.save()

        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, 200)
        # self.assertContains(response, self.user.email)
        self.assertContains(response, 'Welcome to MindTrack')

    def test_mood_record_post_creates_records(self):
        session = self.client.session
        session['user_name'] = self.user.email
        session['user_id'] = self.user.user_id
        session.save()

        response = self.client.post(reverse('mood_record'), {
            'record_date': '2026-03-17',
            'mood_rating': '5',
            'stress_rating': '4',
            'anxiety_rating': '3',
            'note_text': 'Good day'
        })

        self.assertEqual(response.status_code, 200)
        self.assertTrue(
            DailyRecord.objects.filter(
                user=self.user,
                record_date='2026-03-17'
            ).exists()
        )

        daily_record = DailyRecord.objects.get(
            user=self.user,
            record_date='2026-03-17'
        )
        self.assertTrue(
            MoodRecord.objects.filter(
                daily_record=daily_record,
                mood_rating=5,
                stress_rating=4,
                anxiety_rating=3
            ).exists()
        )

    def test_lifestyle_record_post_creates_records(self):
        session = self.client.session
        session['user_name'] = self.user.email
        session['user_id'] = self.user.user_id
        session.save()

        response = self.client.post(reverse('lifestyle_record'), {
            'record_date': '2026-03-17',
            'sleep_time': '2026-03-16T23:00',
            'wake_time': '2026-03-17T07:00',
            'did_exercise': 'on',
            'exercise_type': 'Walking',
            'exercise_duration': '45',
            'workstudy_hours': '3.50'
        })

        self.assertEqual(response.status_code, 200)

        daily_record = DailyRecord.objects.get(
            user=self.user,
            record_date='2026-03-17'
        )

        self.assertTrue(
            SleepRecord.objects.filter(
                daily_record=daily_record
            ).exists()
        )
        self.assertTrue(
            ExerciseRecord.objects.filter(
                daily_record=daily_record,
                did_exercise=True,
                exercise_type='Walking',
                exercise_duration=45
            ).exists()
        )
        self.assertTrue(
            WorkStudyRecord.objects.filter(
                daily_record=daily_record,
                workstudy_hours=Decimal('3.50')
            ).exists()
        )