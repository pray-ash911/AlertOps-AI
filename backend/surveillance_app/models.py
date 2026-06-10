from django.db import models
from django.contrib.auth.models import User

# Choices for Event Status
EVENT_STATUS_CHOICES = [
    ('NEW', 'New'),
    ('REVIEWED', 'Reviewed - Valid'),
    ('FALSE', 'False Alarm'),
    ('CLOSED', 'Closed'),
]

# Lookup Tables

class EventType(models.Model):
    """
    Defines the type of security alert (WEAPON, OVERCROWDING).
    """
    type_id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=50, unique=True)
    description = models.TextField()

    def __str__(self):
        return self.name


class SurveillanceArea(models.Model):
    """
    Defines a monitored physical zone (used for OVERCROWDING).
    """
    area_id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=100)
    overcrowding_threshold = models.IntegerField(default=5)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class User(models.Model):
    username = models.CharField(max_length=150)
    email = models.EmailField()
    password = models.CharField(max_length=128)  # Hashed!
    first_name = models.CharField(max_length=30)
    last_name = models.CharField(max_length=30)
    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)

# Fact and Evidence Tables

class EventLog(models.Model):
    """
    Logs every WEAPON or OVERCROWDING incident.
    """
    log_id = models.AutoField(primary_key=True)

    # Only these two types remain
    type = models.ForeignKey(EventType, on_delete=models.PROTECT)

    # Keep area for OVERCROWDING
    area = models.ForeignKey(
        SurveillanceArea,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Area where the overcrowding occurred."
    )

    timestamp = models.DateTimeField(auto_now_add=True)

    # Weapon → confidence
    # Overcrowding → people count
    confidence_value = models.FloatField()

    status = models.CharField(
        max_length=10,
        choices=EVENT_STATUS_CHOICES,
        default='NEW'
    )

    # Link to admin user who reviewed/closed the event
    reviewed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_events',
        help_text="Admin user who reviewed or handled this event"
    )
    
    reviewed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the event was reviewed/closed by admin"
    )

    def __str__(self):
        """
        String representation of the object

        Query Parameters:
        - None
        - Returns: Description of the event log including timestamp
        """
        return f"{self.type.name} Alert at {self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}"


class EventEvidence(models.Model):
    """
    Stores snapshot images for an event.
    """
    evidence_id = models.AutoField(primary_key=True)
    log = models.ForeignKey(EventLog, on_delete=models.CASCADE, related_name='evidence')
    file_path = models.CharField(max_length=255)
    file_type = models.CharField(max_length=50, default='image/jpeg')

    def __str__(self):
        """
        String representation of the object

        Query Parameters:
        - None
        - Returns: Description of evidence linked to log
        """
        return f"Evidence for Log ID {self.log.log_id}"


# Lift Models

class Lift(models.Model):
    """
    Simple lift model with capacity
    """
    lift_id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=100, unique=True, help_text="e.g., 'Main Lift', 'Service Lift'")
    location = models.CharField(max_length=200, default="Ground Floor", help_text="Building and floor location")

    # Capacity settings
    max_capacity = models.IntegerField(default=5, help_text="Maximum allowed people in lift")
    warning_threshold = models.IntegerField(default=4, help_text="Warning at this count")

    # Status
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} (Max: {self.max_capacity})"

    class Meta:
        verbose_name = "Lift"
        verbose_name_plural = "Lifts"


class LiftUsage(models.Model):
    """
    Tracks each lift usage (one entry per day per lift)
    """
    usage_id = models.AutoField(primary_key=True)
    lift = models.ForeignKey(Lift, on_delete=models.CASCADE, related_name='usages')

    # Counters
    usage_count = models.IntegerField(default=0, help_text="Number of times lift used today")
    total_people = models.IntegerField(default=0, help_text="Total people detected today")

    # Date tracking
    date = models.DateField(auto_now_add=True)  # Automatically set to today

    # Daily stats
    max_people_count = models.IntegerField(default=0, help_text="Maximum people in single detection today")
    overcrowding_count = models.IntegerField(default=0, help_text="Number of overcrowding incidents today")

    # Timestamps
    first_usage = models.DateTimeField(auto_now_add=True)
    last_usage = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.lift.name} - {self.date}: {self.usage_count} uses"

    def update_stats(self, people_count):
        """
        Update statistics with new detection

        Query Parameters:
        - people_count: Number of people detected
        - Returns: None (Updates instance fields)
        """
        self.usage_count += 1
        self.total_people += people_count
        self.max_people_count = max(self.max_people_count, people_count)

        if people_count > self.lift.max_capacity:
            self.overcrowding_count += 1

        self.save()

    def get_avg_people(self):
        """
        Get average people per usage

        Query Parameters:
        - None
        - Returns: Average number of people per lift usage
        """
        return self.total_people / self.usage_count if self.usage_count > 0 else 0

    class Meta:
        unique_together = ['lift', 'date']  # One entry per lift per day
        verbose_name = "Lift Usage"
        verbose_name_plural = "Lift Usages"


class LiftDetection(models.Model):
    """
    Individual lift detection records (supports both image and video)
    """
    SOURCE_TYPE_CHOICES = [
        ('IMAGE', 'Image'),
        ('VIDEO', 'Video'),
    ]

    detection_id = models.AutoField(primary_key=True)
    lift = models.ForeignKey(Lift, on_delete=models.CASCADE, related_name='detections')
    usage = models.ForeignKey(LiftUsage, on_delete=models.CASCADE, related_name='detections', null=True, blank=True)

    # Source type
    source_type = models.CharField(max_length=10, choices=SOURCE_TYPE_CHOICES, default='IMAGE')

    # Detection results
    people_count = models.IntegerField()
    is_overcrowded = models.BooleanField(default=False)
    confidence_score = models.FloatField()

    # Media files
    image = models.ImageField(upload_to='lift_detections/', blank=True, null=True)
    video = models.FileField(upload_to='lift_videos/', blank=True, null=True)
    processed_image = models.CharField(max_length=255, blank=True, help_text="Path to annotated peak frame image")

    # Detection details
    detection_data = models.JSONField(default=dict, blank=True)  # Store boxes, confidences, etc.

    # Video-specific results
    frame_results = models.JSONField(default=list, blank=True, help_text="Per-frame detection results for video")
    max_people_in_video = models.IntegerField(default=0, help_text="Max people detected in any single frame")
    avg_people_in_video = models.FloatField(default=0.0, help_text="Average people across sampled frames")
    processed_video = models.CharField(max_length=255, blank=True, null=True, help_text="Path to annotated video file")

    # Metadata
    timestamp = models.DateTimeField(auto_now_add=True)
    processing_time = models.FloatField(default=0.0, help_text="Processing time in seconds")

    def __str__(self):
        """
        String representation of the object

        Query Parameters:
        - None
        - Returns: Detection summary string
        """
        status = "OVERLOADED" if self.is_overcrowded else "OK"
        return f"{self.lift.name}: {self.people_count} people ({status})"

    def get_status_color(self):
        """
        Get color based on overcrowding status

        Query Parameters:
        - None
        - Returns: Color string ('red', 'orange', or 'green')
        """
        if self.is_overcrowded:
            return "red"
        elif self.people_count >= self.lift.warning_threshold:
            return "orange"
        else:
            return "green"

    class Meta:
        ordering = ['-timestamp']
        verbose_name = "Lift Detection"
        verbose_name_plural = "Lift Detections"
