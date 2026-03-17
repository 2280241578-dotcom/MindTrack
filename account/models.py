from django.db import models
import random
from django.contrib.auth.hashers import check_password, make_password
# from .models import User

def gen_user_code():
    # 生成 6 位数字字符串 Generate a 6-digit string of numbers
    return ''.join(random.choices('0123456789', k=6))

# 1、登陆注册表 user
class User(models.Model):
    email = models.CharField(max_length=100, unique=True, blank=False)
    password = models.CharField(max_length=100, blank=True, null=True)

    # 6位用户编号（唯一） Six user identification numbers (unique)
    user_id = models.CharField(max_length=6, primary_key=True,editable=False)

    # 个人资料（允许空，注册后在个人中心补） Personal Information (Optional. Fill in in Personal Center after registration)
    username = models.CharField(max_length=50, null=True, blank=True)
    age = models.PositiveSmallIntegerField(null=True, blank=True)

    # 你也可以用 choices，防止用户乱填
    GENDER_CHOICES = (
        ('male', 'Male'),
        ('female', 'Female'),
        ('other', 'Other'),
        ('na', 'Prefer not to say'),
    )
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES, null=True, blank=True)

    sleep_preference = models.CharField(max_length=50, null=True, blank=True)  # 输入睡眠习惯 Enter sleep habits

    def save(self, *args, **kwargs):
        # 第一次保存时生成 user_id，并确保唯一  When saving for the first time, a user_id is generated and it is ensured to be unique.
        if not self.user_id:
            while True:
                code = gen_user_code()
                if not User.objects.filter(user_id=code).exists():
                    self.user_id = code
                    break
        super().save(*args, **kwargs)


    def set_password(self, password):
        # 对密码进行加密 Encrypt the password
        self.password = make_password(password)
        self.save()

    def check_password(self, password):
        # 对密码进行验证 Verify the password
        return check_password(password, self.password)

    def __str__(self):
        return self.email





#2、dailyrecord表
class DailyRecord(models.Model):
    # record_id（主键 primary key）
    record_id = models.AutoField(primary_key=True)

    # user_id（外键 → 指向 User.user_id   Foreign key → pointing to User.user_id）
    user = models.ForeignKey(
        User,
        # user,
        on_delete=models.CASCADE,
        db_column='user_id'   # 数据库列名就叫 user_id
    )

    # record_data（当天日期，年月日   Date of the day, Year Month Day）
    record_date = models.DateField()

    class Meta:
        # 同一个用户同一天只能有一条记录  The same user can only have one record on the same day
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'record_date'],
                name='unique_user_per_day'
            )
        ]

    def __str__(self):
        return f"{self.user.user_id} - {self.record_date}"





#3、moodrecord表
class MoodRecord(models.Model):

    daily_record = models.OneToOneField(
        DailyRecord,
        on_delete=models.CASCADE
    )

    # Mood：越大越好  mood:The bigger, the better.
    MOOD_CHOICES = [
        (1, 'Very Low Mood'),
        (2, 'Low Mood'),
        (3, 'Neutral'),
        (4, 'Good Mood'),
        (5, 'Very Good Mood'),
    ]

    # Stress：越大压力越低（越健康） stress:The greater the pressure, the lower the pressure (healthier)
    STRESS_CHOICES = [
        (1, 'Very High Stress'),
        (2, 'High Stress'),
        (3, 'Moderate Stress'),
        (4, 'Low Stress'),
        (5, 'Very Low Stress'),
    ]

    # Anxiety：越大焦虑越低（越健康）  anxiety:The greater the anxiety, the lower (healthier) it is
    ANXIETY_CHOICES = [
        (1, 'Very High Anxiety'),
        (2, 'High Anxiety'),
        (3, 'Moderate Anxiety'),
        (4, 'Low Anxiety'),
        (5, 'Very Low Anxiety'),
    ]

    mood_rating = models.PositiveSmallIntegerField(choices=MOOD_CHOICES)
    stress_rating = models.PositiveSmallIntegerField(choices=STRESS_CHOICES)
    anxiety_rating = models.PositiveSmallIntegerField(choices=ANXIETY_CHOICES)

    note_text = models.TextField(null=True, blank=True)

    def __str__(self):
        return f"{self.daily_record.record_date} - {self.daily_record.user.user_id}"





#4、sleeprecord表
# sleeprecord表支持：（用户在入睡填写一次入睡时间，用户在起床后填写起床时间，
# 然后daily_record归属于“起床时间”的那天（格式：年月日），并且能计算sleep_duration睡眠时长，然后能查到用户哪天的睡眠时长）这样的结构，
# 但是要实现这个操作（daily_record属于哪天、计算睡眠时长和查找用户哪天的睡眠时长）需要在view.py里写代码来实现功能
# 用户未填写起床时间导致有未完成填写数据的情况的解决方案：
# 第一天用户填写入睡时间：创建记录（status=open）
#第二天忘记填起床时间：这条记录保持 status=open
# 第三天再次填写入睡时间：你需要在 view.py 里写代码实现：把旧 open 标记为 abandoned，然后再创建新的 open（新的 sleep_id）
# 第四天起床后填写起床时间：wake_time，然后在view.py里写代码实现：计算 sleep_duration，把open标记为complete（status=complete）
# 仍然用 record_id 连接 DailyRecord.record_id
class SleepRecord(models.Model):

    # 主键  primary key
    sleep_id = models.AutoField(primary_key=True)

    # 外键 → 连接 DailyRecord.record_id   Foreign key → Connect DailyRecord.record_id
    daily_record = models.OneToOneField(
        DailyRecord,
        on_delete=models.CASCADE,
        db_column='daily_record'
    )

    # 状态：open=未完成，complete=已完成，abandoned=已废弃
    STATUS_CHOICES = [
        ("open", "Open"),
        ("complete", "Complete"),
        ("abandoned", "Abandoned"),
    ]
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="open"
    )

    # 入睡时间（第一次填写）
    sleep_time = models.DateTimeField()

    # 起床时间（第二次填写时才有）
    wake_time = models.DateTimeField(null=True, blank=True)

    # 睡眠时长（单位：分钟）
    sleep_duration = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["status"]),  #对status建索引，当你查询时数据库可以很快找到所有 complete 的记录
            models.Index(fields=["sleep_time"]),  #对sleep_time建索引，当你按时间排序或查询范围会更快
        ]

    def __str__(self):
        return f"{self.daily_record.record_date} - {self.daily_record.user.user_id}"





#5、exerciserecord表
#exerciserecord表实现：用户可以填写他今天是否运行（是/否）运动了选勾，没运动选叉，填写运动时长和运动类型，
# 表里有did_exercise、exercise_id、daily_record、exercisse_type、exercise_duration，
# 允许用户不填写exercisse_type、exercise_duration（万一用户忘了填写），
# daily_record是dailyrecord表里的record_id的外键，这样用户就可以查哪天是否运动、运动类型和运动时长。
# 在前端，是否运动的勾和叉传到后端的did_exercise是True和False，但需要在前端里写，表只是接收数据
class ExerciseRecord(models.Model):
    exercise_id = models.AutoField(primary_key=True)

    # 连接 DailyRecord.record_id（外键/一对一）
    daily_record = models.OneToOneField(
        DailyRecord,
        on_delete=models.CASCADE,
        db_column='daily_record'
    )

    # 是否运动：在前端要显示：运动选：勾，没有运动选：叉，表里True表示勾，False表示叉
    did_exercise = models.BooleanField(default=False)  #1->true 2->false

    # 运动类型（可不填）
    exercise_type = models.CharField(max_length=50, null=True, blank=True)

    # 运动时长（分钟，可不填）
    exercise_duration = models.PositiveSmallIntegerField(null=True, blank=True)

    def __str__(self):
        return f"{self.daily_record.record_date} - {self.daily_record.user.user_id} - exercise={self.did_exercise}"





#6、workstudyrecord表
class WorkStudyRecord(models.Model):
    workstudy_id = models.AutoField(primary_key=True)

    # 外键 → 连接 DailyRecord.record_id
    daily_record = models.OneToOneField(
        DailyRecord,
        on_delete=models.CASCADE,
        db_column='daily_record'
    )

    # 今天工作/学习时长（小时）
    workstudy_hours = models.DecimalField(max_digits=4, decimal_places=2)

    def __str__(self):
        return f"{self.daily_record.record_date} - {self.daily_record.user.user_id} - {self.workstudy_hours}h"











