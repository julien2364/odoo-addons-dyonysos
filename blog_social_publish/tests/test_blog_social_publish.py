# -*- coding: utf-8 -*-
"""Tests fonctionnels de Blog to Social.

Aucun appel réseau réel : ``requests.post`` est systématiquement simulé.
"""

import json
from datetime import timedelta
from unittest.mock import patch

from odoo import fields
from odoo.exceptions import UserError
from odoo.tests import TransactionCase, tagged
from odoo.tools import mute_logger

PATCH_TARGET = "odoo.addons.blog_social_publish.models.blog_social_post.requests.post"


class FakeResponse:
    """Réponse HTTP minimale, compatible avec ce que le module lit."""

    def __init__(self, status_code=200, payload=None, text=None):
        self.status_code = status_code
        self._payload = payload if payload is not None else {"id": "REMOTE-1"}
        self.text = text if text is not None else json.dumps(self._payload)

    def json(self):
        if self._payload is None:
            raise ValueError("no json")
        return self._payload


@tagged("post_install", "-at_install")
class TestBlogSocialPublish(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.params = cls.env["ir.config_parameter"].sudo()
        cls.params.set_param("web.base.url", "https://example.com")
        # Activation figée hier : les articles créés pendant les tests sont récents.
        cls.activation = fields.Datetime.now() - timedelta(days=1)
        cls.params.set_param(
            "blog_social_publish.activation_date",
            fields.Datetime.to_string(cls.activation))
        cls.params.set_param("blog_social_publish.auto_publish", "True")

        cls.blog_a = cls.env["blog.blog"].create({"name": "Blog A"})
        cls.blog_b = cls.env["blog.blog"].create({"name": "Blog B"})

        Channel = cls.env["blog.social.channel"]
        cls.channel_hook = Channel.create({
            "name": "LinkedIn via n8n",
            "network": "linkedin",
            "transport": "webhook",
            "webhook_url": "https://n8n.example.com/webhook/blog",
            "webhook_headers": '{"X-Source": "odoo"}',
            "webhook_auth_header": "Bearer secret-token",
            "message_template": "{title}\n\n{teaser}\n\n{url}\n{hashtags}",
            "hashtags": "odoo, blog",
            "max_length": 3000,
            "utm_source": "linkedin",
            "utm_medium": "social",
            "utm_campaign": "blog",
        })
        cls.channel_postiz = Channel.create({
            "name": "X via Postiz",
            "network": "x",
            "transport": "postiz",
            "postiz_base_url": "https://postiz.example.com/",
            "postiz_api_key": "POSTIZ-KEY",
            "postiz_integration_id": "integration-42",
            "message_template": "{title} {url}",
            "max_length": 280,
        })

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    @classmethod
    def _create_post(cls, blog=None, published=True, **values):
        vals = {
            "name": "Odoo 19 en production",
            "subtitle": "Retour d'expérience",
            "blog_id": (blog or cls.blog_a).id,
            "content": "<p>%s</p>" % ("Un contenu de démonstration. " * 20),
        }
        vals.update(values)
        post = cls.env["blog.post"].create(vals)
        if published:
            post.write({"is_published": True})
        return post

    def _social(self, post):
        return self.env["blog.social.post"].search([("post_id", "=", post.id)])

    # ------------------------------------------------------------------
    # 1. Une publication par canal concerné
    # ------------------------------------------------------------------
    def test_01_publish_creates_one_post_per_channel(self):
        post = self._create_post()
        social = self._social(post)
        self.assertEqual(len(social), 2, "Un enregistrement par canal actif")
        self.assertEqual(social.mapped("channel_id"), self.channel_hook | self.channel_postiz)
        self.assertEqual(set(social.mapped("state")), {"queued"})
        self.assertTrue(all(social.mapped("message")))

    # ------------------------------------------------------------------
    # 2. Cloisonnement par blog
    # ------------------------------------------------------------------
    def test_02_channel_restricted_to_one_blog(self):
        self.channel_postiz.blog_ids = self.blog_b
        post = self._create_post(blog=self.blog_a)
        social = self._social(post)
        self.assertEqual(len(social), 1)
        self.assertEqual(social.channel_id, self.channel_hook)

        other = self._create_post(blog=self.blog_b)
        self.assertEqual(
            self._social(other).mapped("channel_id"),
            self.channel_hook | self.channel_postiz,
            "Un canal sans restriction reçoit tous les blogs")

    # ------------------------------------------------------------------
    # 3. Garde-fou : aucune publication rétroactive
    # ------------------------------------------------------------------
    def test_03_no_retroactive_publication(self):
        old = self.activation - timedelta(days=365)
        post = self._create_post(published=False)
        post.write({"is_published": True, "published_date": old})
        self.assertEqual(post.post_date, old)
        self.assertFalse(
            self._social(post),
            "Un article publié avant l'activation du module ne doit jamais partir")

        # ... alors qu'un article récent passe bien.
        recent = self._create_post()
        self.assertTrue(self._social(recent))

    # ------------------------------------------------------------------
    # 4. auto_publish désactivé
    # ------------------------------------------------------------------
    def test_04_auto_publish_disabled_but_manual_works(self):
        self.params.set_param("blog_social_publish.auto_publish", "False")
        post = self._create_post()
        self.assertFalse(self._social(post), "Rien ne part tant que auto_publish est décoché")

        action = post.action_blog_social_publish()
        social = self._social(post)
        self.assertEqual(len(social), 2, "Le bouton manuel crée bien les publications")
        self.assertEqual(action["res_model"], "blog.social.post")

        # Le bouton refuse un article non publié sur le site.
        draft = self._create_post(published=False)
        with self.assertRaises(UserError):
            draft.action_blog_social_publish()

    # ------------------------------------------------------------------
    # 5. Rendu du gabarit
    # ------------------------------------------------------------------
    def test_05_message_rendering(self):
        self.channel_hook.message_template = (
            "{title} — {subtitle}\n{blog} par {author}\n{teaser}\n{url}\n{hashtags}")
        post = self._create_post()
        social = self._social(post).filtered(lambda s: s.channel_id == self.channel_hook)
        message = social.message

        self.assertIn("Odoo 19 en production", message)
        self.assertIn("Retour d'expérience", message)
        self.assertIn("Blog A", message)
        self.assertIn(post.author_id.name, message)
        self.assertIn("Un contenu de démonstration", message)
        self.assertIn("#odoo", message)
        self.assertIn("#blog", message)
        self.assertNotIn("{", message, "Toutes les variables doivent être remplacées")

        self.assertTrue(social.link.startswith("https://example.com/blog/"))
        self.assertIn("utm_source=linkedin", social.link)
        self.assertIn("utm_medium=social", social.link)
        self.assertIn("utm_campaign=blog", social.link)
        self.assertIn(social.link, message)

    # ------------------------------------------------------------------
    # 6. Troncature propre
    # ------------------------------------------------------------------
    def test_06_truncation_keeps_url_and_words(self):
        post = self._create_post()
        social = self._social(post).filtered(lambda s: s.channel_id == self.channel_postiz)
        channel = self.channel_postiz
        channel.message_template = "{title}. {teaser} {url}"
        long_text = "Alphabet " * 60
        link = "https://example.com/blog/blog-a-1/un-article-au-titre-tres-long-2"
        message = self.env["blog.social.post"]._truncate_message(
            "%s%s" % (long_text, link), link, 280)

        self.assertLessEqual(len(message), 280)
        self.assertIn(link, message, "Le lien doit rester entier")
        self.assertTrue(message.endswith(link))
        body = message[: -len(link)].rstrip()
        self.assertTrue(body.endswith("…"))
        for word in body[:-1].split():
            self.assertIn(word, long_text, "Aucun mot ne doit être coupé")

        # Cas réel via le canal : le message stocké respecte la limite.
        rendered = self.env["blog.social.post"]._render_message(post, channel)
        self.assertLessEqual(len(rendered), channel.max_length)
        self.assertIn(social.link, rendered)

    # ------------------------------------------------------------------
    # 7. Transport Postiz
    # ------------------------------------------------------------------
    def test_07_postiz_transport(self):
        post = self._create_post()
        social = self._social(post).filtered(lambda s: s.channel_id == self.channel_postiz)
        with patch(PATCH_TARGET, return_value=FakeResponse(
                200, {"id": "postiz-777"})) as mocked:
            social.action_send_now()
        self.assertEqual(mocked.call_count, 1)
        args, kwargs = mocked.call_args
        self.assertEqual(args[0], "https://postiz.example.com/api/public/v1/posts")
        self.assertEqual(kwargs["headers"]["Authorization"], "POSTIZ-KEY")
        self.assertTrue(kwargs["timeout"])
        body = kwargs["json"]
        self.assertEqual(body["posts"][0]["integration"]["id"], "integration-42")
        self.assertEqual(body["posts"][0]["value"][0]["content"], social.message)

        self.assertEqual(social.state, "sent")
        self.assertEqual(social.remote_id, "postiz-777")
        self.assertTrue(social.sent_date)
        self.assertFalse(social.error)

    # ------------------------------------------------------------------
    # 8. Transport webhook
    # ------------------------------------------------------------------
    def test_08_webhook_transport(self):
        post = self._create_post()
        social = self._social(post).filtered(lambda s: s.channel_id == self.channel_hook)
        with patch(PATCH_TARGET, return_value=FakeResponse(200, {"id": "hook-1"})) as mocked:
            social.action_send_now()
        args, kwargs = mocked.call_args
        self.assertEqual(args[0], "https://n8n.example.com/webhook/blog")
        headers = kwargs["headers"]
        self.assertEqual(headers["X-Source"], "odoo")
        self.assertEqual(headers["Authorization"], "Bearer secret-token")
        self.assertEqual(headers["Content-Type"], "application/json")

        body = kwargs["json"]
        for key in ("message", "title", "url", "image_url", "network", "blog",
                    "blog_id", "post_id", "author"):
            self.assertIn(key, body)
        self.assertEqual(body["title"], post.name)
        self.assertEqual(body["post_id"], post.id)
        self.assertEqual(body["network"], "linkedin")
        self.assertEqual(body["blog"], "Blog A")
        self.assertEqual(social.state, "sent")

    # ------------------------------------------------------------------
    # 9. Erreur HTTP
    # ------------------------------------------------------------------
    @mute_logger("odoo.addons.blog_social_publish.models.blog_social_post")
    def test_09_http_error_is_logged_not_raised(self):
        post = self._create_post()
        social = self._social(post).filtered(lambda s: s.channel_id == self.channel_hook)
        with patch(PATCH_TARGET, return_value=FakeResponse(
                500, {"message": "boom"}, text="Internal Server Error")):
            social.action_send_now()  # ne doit lever aucune exception
        self.assertEqual(social.state, "error")
        self.assertIn("500", social.error)
        self.assertEqual(social.retry_count, 1)
        self.assertTrue(post.is_published, "L'article n'est pas modifié par l'échec")
        self.assertFalse(social.sent_date)

        # Une erreur réseau (exception) est traitée de la même façon.
        with patch(PATCH_TARGET, side_effect=OSError("connection refused")):
            social.action_send_now()
        self.assertEqual(social.state, "error")
        self.assertIn("connection refused", social.error)

    # ------------------------------------------------------------------
    # 10. Tâche planifiée
    # ------------------------------------------------------------------
    def test_10_cron_respects_schedule_and_sends_once(self):
        post = self._create_post()
        social = self._social(post)
        later = social.filtered(lambda s: s.channel_id == self.channel_postiz)
        now_due = social - later
        later.scheduled_date = fields.Datetime.now() + timedelta(hours=6)
        now_due.scheduled_date = fields.Datetime.now() - timedelta(minutes=5)

        with patch(PATCH_TARGET, return_value=FakeResponse()) as mocked:
            self.env["blog.social.post"]._cron_process_queue()
        self.assertEqual(mocked.call_count, 1, "Seule la publication due est envoyée")
        self.assertEqual(now_due.state, "sent")
        self.assertEqual(later.state, "queued")

        # Deuxième passage : rien de plus n'est envoyé pour la publication déjà partie.
        with patch(PATCH_TARGET, return_value=FakeResponse()) as mocked:
            self.env["blog.social.post"]._cron_process_queue()
        self.assertEqual(mocked.call_count, 0)
        self.assertEqual(now_due.state, "sent")

    # ------------------------------------------------------------------
    # 11. Backoff : plus de rejeu au-delà de 5 tentatives
    # ------------------------------------------------------------------
    @mute_logger("odoo.addons.blog_social_publish.models.blog_social_post")
    def test_11_no_replay_after_max_retry(self):
        post = self._create_post()
        social = self._social(post).filtered(lambda s: s.channel_id == self.channel_hook)
        (self._social(post) - social).action_cancel()
        with patch(PATCH_TARGET, return_value=FakeResponse(500, text="ko")) as mocked:
            for _index in range(8):
                self.env["blog.social.post"]._cron_process_queue()
        self.assertEqual(social.state, "error")
        self.assertEqual(social.retry_count, 5, "Au plus 5 tentatives")
        self.assertEqual(mocked.call_count, 5)

        # Une remise en file manuelle réarme le compteur.
        social.action_requeue()
        self.assertEqual(social.retry_count, 0)
        self.assertEqual(social.state, "queued")

    # ------------------------------------------------------------------
    # 12. Contrainte d'unicité (article, canal)
    # ------------------------------------------------------------------
    @mute_logger("odoo.sql_db")
    def test_12_unique_post_channel(self):
        post = self._create_post()
        social = self._social(post)[0]
        with self.assertRaises(Exception):
            with self.env.cr.savepoint():
                self.env["blog.social.post"].create({
                    "post_id": social.post_id.id,
                    "channel_id": social.channel_id.id,
                })

    # ------------------------------------------------------------------
    # 13. Dépublier puis republier ne crée pas de doublon
    # ------------------------------------------------------------------
    def test_13_unpublish_republish_no_duplicate(self):
        post = self._create_post()
        self.assertEqual(len(self._social(post)), 2)
        post.write({"is_published": False})
        post.write({"is_published": True})
        self.assertEqual(len(self._social(post)), 2, "Aucun doublon après republication")
        post.action_blog_social_publish()
        self.assertEqual(len(self._social(post)), 2)

    # ------------------------------------------------------------------
    # 14. Bouton « Tester le canal »
    # ------------------------------------------------------------------
    def test_14_test_channel_button(self):
        with patch(PATCH_TARGET, return_value=FakeResponse(200, {"id": "ping"})) as mocked:
            action = self.channel_hook.action_test_channel()
        self.assertEqual(mocked.call_count, 1)
        self.assertEqual(action["params"]["type"], "success")
        self.assertFalse(
            self.env["blog.social.post"].search([]),
            "Le test ne crée aucune publication")

    # ------------------------------------------------------------------
    # 15. Image de couverture et champs protégés
    # ------------------------------------------------------------------
    def test_15_cover_image_and_secret_fields(self):
        post = self._create_post(published=False)
        post.cover_properties = json.dumps(
            {"background-image": "url('/web/image/1234-abc/cover.jpg')"})
        post.write({"is_published": True})
        social = self._social(post).filtered(lambda s: s.channel_id == self.channel_hook)
        self.assertEqual(social.image_url, "https://example.com/web/image/1234-abc/cover.jpg")

        # Les secrets sont réservés à base.group_system au niveau du champ.
        for model, fname in (("blog.social.channel", "postiz_api_key"),
                             ("blog.social.channel", "webhook_url"),
                             ("blog.social.channel", "webhook_auth_header")):
            field = self.env[model]._fields[fname]
            self.assertEqual(field.groups, "base.group_system", fname)
