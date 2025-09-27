#!/usr/bin/env python3
"""
Celery Worker dla przetwarzania feedów Amazon
"""

from tasks.feed_processing import celery_app

if __name__ == '__main__':
    celery_app.start()