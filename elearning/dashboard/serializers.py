from rest_framework import serializers


class DashboardModuleSer(serializers.Serializer):
    id = serializers.CharField()
    title = serializers.CharField()
    study_time_hours = serializers.FloatField()
    lessons_done = serializers.IntegerField()
    lessons_total = serializers.IntegerField()
    progress_percent = serializers.IntegerField()


class DashboardEventSer(serializers.Serializer):
    id = serializers.CharField()
    title = serializers.CharField()
    date_iso = serializers.DateField(format="%Y-%m-%d")
    type = serializers.ChoiceField(choices=["Meilenstein", "Prüfung", "Aufgabe"])


class DashboardSer(serializers.Serializer):
    greeting_name = serializers.CharField()
    week_streak_days = serializers.IntegerField()
    weekly_learning_hours = serializers.FloatField()
    modules_completed = serializers.IntegerField()
    current_goal_percent = serializers.IntegerField()
    active_modules = DashboardModuleSer(many=True)
    upcoming_events = DashboardEventSer(many=True)
