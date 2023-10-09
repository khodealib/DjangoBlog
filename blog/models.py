from django.contrib.contenttypes.fields import GenericRelation
from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.html import format_html

from account.models import User
from comment.models import Comment
from extensions.utils import jalali_converter


# my managers
class ArticleManager(models.Manager):
    def published(self):
        return self.filter(status='p')


class CategoryManager(models.Manager):
    def active(self):
        return self.filter(status=True)


# Create your models here.
class IPAddress(models.Model):
    ip_address = models.GenericIPAddressField(verbose_name="آدرس آی‌پی")


class Category(models.Model):
    parent = models.ForeignKey(
        'self',
        default=None,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='children',
        verbose_name="زیردسته"
    )
    title = models.CharField(max_length=200, verbose_name="عنوان دسته‌بندی")
    slug = models.SlugField(
        max_length=100,
        unique=True,
        verbose_name="آدرس دسته‌بندی"
    )
    status = models.BooleanField(
        default=True,
        verbose_name="آیا نمایش داده شود؟"
    )
    position = models.IntegerField(verbose_name="پوزیشن")

    class Meta:
        verbose_name = "دسته‌بندی"
        verbose_name_plural = "دسته‌بندی ها"
        ordering = ['parent__id', 'position']

    def __str__(self):
        return self.title

    objects = CategoryManager()


class Article(models.Model):
    STATUS_CHOICES = (
        ('d', 'پیش‌نویس'),  # draft
        ('p', "منتشر شده"),  # publish
        ('i', "در حال بررسی"),  # investigation
        ('b', "برگشت داده شده"),  # back
    )
    author = models.ForeignKey(
        User,
        null=True,
        on_delete=models.SET_NULL,
        related_name='articles',
        verbose_name="نویسنده"
    )
    title = models.CharField(max_length=200, verbose_name="عنوان مقاله")
    slug = models.SlugField(
        max_length=100,
        unique=True,
        verbose_name="آدرس مقاله"
    )
    category = models.ManyToManyField(
        Category,
        verbose_name="دسته‌بندی",
        related_name="articles"
    )
    description = models.TextField(verbose_name="محتوا")
    thumbnail = models.ImageField(
        upload_to="images",
        verbose_name="تصویر مقاله"
    )
    publish = models.DateTimeField(
        default=timezone.now,
        verbose_name="زمان انتشار"
    )
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    is_special = models.BooleanField(default=False, verbose_name="مقاله ویژه")
    status = models.CharField(
        max_length=1,
        choices=STATUS_CHOICES,
        verbose_name="وضعیت"
    )
    comments = GenericRelation(Comment)
    hits = models.ManyToManyField(
        IPAddress,
        through="ArticleHit",
        blank=True,
        related_name="hits",
        verbose_name="بازدیدها"
    )

    class Meta:
        verbose_name = "مقاله"
        verbose_name_plural = "مقالات"
        ordering = ['-publish']

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse("account:home")

    def jpublish(self):
        return jalali_converter(self.publish)

    jpublish.short_description = "زمان انتشار"

    def thumbnail_tag(self):
        return format_html(
            "<img width=100 height=75 style='border-radius: 5px;' src='{}'>"
            .format(
                self.thumbnail.url
            )
        )

    thumbnail_tag.short_description = "عکس"

    def category_to_str(self):
        return "، ".join(
            [category.title for category in self.category.active()]
        )

    category_to_str.short_description = "دسته‌بندی"

    objects = ArticleManager()


class ArticleHit(models.Model):
    article = models.ForeignKey(Article, on_delete=models.CASCADE)
    ip_address = models.ForeignKey(IPAddress, on_delete=models.CASCADE)
    created = models.DateTimeField(auto_now_add=True)
