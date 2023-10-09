from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.sites.shortcuts import get_current_site
from django.core.exceptions import PermissionDenied
from django.core.mail import EmailMessage
from django.http import JsonResponse, HttpResponseBadRequest
from django.shortcuts import render, get_object_or_404
from django.template.loader import render_to_string
from django.urls import reverse
from django.views.generic import FormView

from comment.forms import CommentForm
from comment.models import Comment
from comment.utils import (
    get_comment_context_data, get_model_obj,
    is_comment_admin, is_comment_moderator
)


class BaseCommentView(LoginRequiredMixin, FormView):
    form_class = CommentForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['comment_form'] = context.pop('form')
        context.update(get_comment_context_data(self.request))
        return context

    def post(self, request, *args, **kwargs):
        if not request.is_ajax():
            return HttpResponseBadRequest('Only AJAX request are allowed')
        return super().post(request, *args, **kwargs)


class CreateComment(BaseCommentView):
    comment = None

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['comment'] = self.comment
        return context

    def get_template_names(self):
        if self.comment.is_parent:
            return ['comment/comments/base.html']
        else:
            return ['comment/comments/child_comment.html']

    def form_valid(self, form):
        app_name = self.request.POST.get('app_name')
        model_name = self.request.POST.get('model_name')
        model_id = self.request.POST.get('model_id')
        model_object = get_model_obj(app_name, model_name, model_id)
        parent_id = self.request.POST.get('parent_id')
        parent_comment = None
        if parent_id:
            parent_qs = Comment.objects.filter(id=parent_id)
            if parent_qs.exists():
                parent_comment = parent_qs.first()
        comment_content = form.cleaned_data['content']
        self.comment = Comment.objects.create(
            content_object=model_object,
            content=comment_content,
            user=self.request.user,
            parent=parent_comment,
        )

        # send email section
        current_site = get_current_site(self.request)
        article = self.comment.content_object
        author_email = article.author.email
        user_email = self.comment.user.email
        if author_email == user_email:
            author_email = False
            user_email = False
        parent_email = False
        if self.comment.parent:
            parent_email = self.comment.parent.user.email
            if parent_email in [author_email, user_email]:
                parent_email = False

        if author_email:
            email = EmailMessage(
                "دیدگاه جدید",
                "دیدگاه جدیدی برای مقاله «{}» که شما نوینده آن هستید، ارسال شده:\n{}{}".format(
                    article, current_site,
                    reverse('blog:detail', kwargs={'slug': article.slug})
                ),
                to=[author_email]
            )
            email.send()

        if user_email:
            email = EmailMessage(
                "دیدگاه دریافت شد",
                "دیدگاه شما دریافت شد و به زودی به آن پاسخ می دهیم.",
                to=[user_email]
            )
            email.send()

        if parent_email:
            email = EmailMessage(
                "پاسخ به دیدگاه شما",
                "پاسخی به دیدگاه شما در مقاله «{}» ثبت شده است. برای مشاهده بر روی لینک زیر کلیک کنید:\n{}{}".format(
                    article, current_site,
                    reverse('blog:detail', kwargs={'slug': article.slug})),
                to=[parent_email]
            )
            email.send()

        return self.render_to_response(self.get_context_data())


class UpdateComment(BaseCommentView):
    comment = None

    def dispatch(self, request, *args, **kwargs):
        self.comment = get_object_or_404(Comment, pk=self.kwargs.get('pk'))
        if request.user != self.comment.user:
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        context = self.get_context_data()
        context['comment_form'] = CommentForm(instance=self.comment)
        context['comment'] = self.comment
        return render(request, 'comment/comments/update_comment.html', context)

    def post(self, request, *args, **kwargs):
        form = CommentForm(request.POST, instance=self.comment)
        context = self.get_context_data()
        if form.is_valid():
            form.save()
            context['comment'] = self.comment
            return render(request, 'comment/comments/comment_content.html',
                          context)


class DeleteComment(BaseCommentView):
    comment = None

    def dispatch(self, request, *args, **kwargs):
        self.comment = get_object_or_404(Comment, pk=self.kwargs.get('pk'))
        if request.user != self.comment.user and not is_comment_admin(
                request.user) \
                and not (self.comment.is_flagged and is_comment_moderator(
            request.user)):
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        data = dict()
        context = self.get_context_data()
        context["comment"] = self.comment
        data['html_form'] = render_to_string(
            'comment/comments/comment_modal.html', context, request=request)
        return JsonResponse(data)

    def post(self, request, *args, **kwargs):
        self.comment.delete()
        context = self.get_context_data()
        return render(request, 'comment/comments/base.html', context)
