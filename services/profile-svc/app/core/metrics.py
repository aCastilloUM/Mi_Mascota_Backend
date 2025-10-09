from prometheus_client import Counter, Histogram

profile_write_counter = Counter(
    "profiles_write_total",
    "Total profile write operations",
    labelnames=["action", "outcome"],
)

profile_history_counter = Counter(
    "profiles_history_total",
    "Profile history records created",
    labelnames=["action"],
)

profile_photo_upload_duration = Histogram(
    "profiles_photo_upload_seconds",
    "Time spent processing profile photo uploads.",
)

profile_photo_upload_total = Counter(
    "profiles_photo_upload_total",
    "Total profile photo uploads",
    labelnames=["outcome"],
)
