from django.dispatch import Signal

# fired after a comment is successfully persisted
comment_created = Signal()
