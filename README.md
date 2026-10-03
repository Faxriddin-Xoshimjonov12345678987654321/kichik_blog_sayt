# Kichik blog sayt (Django REST Framework)

Django 5.2, DRF, JWT (simplejwt), MySQL.

## Ishga tushirish

1. `pip install -r requirements.txt`
2. MySQL'da `myblog` bazasini yarating (sozlamalar `conf/settings.py` ichida)
3. `python manage.py migrate`
4. `python manage.py createsuperuser`
5. `python manage.py runserver`
6. Testlar: `python manage.py test`

Admin panelda kategoriyalarni (`Category`) yarating. Superuser `is_staff` bo'lgani uchun post yoza oladi.

## Ro'yxatdan o'tish oqimi

`signup` -> `verify` -> `change-user-info` -> `change-photo` -> `login`

Holatlar: `new` -> `code_verify` -> `done` -> `photo_done`. Post yozish uchun kamida `done` kerak.
Kod hozircha konsolga chiqadi (`EMAIL CODE: ...`).

## Accounts: `/accounts/`

| Metod | URL | Tavsif |
|---|---|---|
| POST | `signup/` | `email_or_phone_number` yuboriladi, token qaytadi |
| POST | `verify/` | `code` (4 raqam), Bearer token bilan |
| GET | `resend-code/` | Yangi kod yuborish |
| PUT | `change-user-info/` | first_name, last_name, username, password, confirm_password |
| PUT | `change-photo/` | `photo` (jpg/jpeg/png, 5 MB gacha), multipart |
| POST | `login/` | `userinput` (username/email/telefon) va `password` |
| POST | `logout/` | `refresh` tokenni blacklistga qo'shadi |
| POST | `token/refresh/` | Yangi access token |
| PUT | `change-password/` | old_password, new_password, confirm_password |
| GET, PATCH | `me/` | Profil |

## Blog: `/blog/`

| Metod | URL | Tavsif |
|---|---|---|
| GET | `categories/` | Kategoriyalar va postlar soni |
| GET | `tags/` | Teglar (mashhurlik bo'yicha) |
| GET | `posts/` | Chop etilgan postlar |
| POST | `posts/` | Post yaratish (tasdiqlangan foydalanuvchi) |
| GET | `posts/<slug>/` | Post (ko'rishlar soni oshadi) |
| PUT, PATCH, DELETE | `posts/<slug>/` | Faqat muallif |
| POST | `posts/<slug>/like/` | Like qo'yish / olib tashlash |
| POST | `posts/<slug>/bookmark/` | Saqlash / olib tashlash |
| GET | `posts/my/` | Mening postlarim (qoralamalar bilan), `?status=draft` |
| GET | `posts/bookmarks/` | Saqlangan postlar |
| GET | `my-stats/` | Postlar, ko'rishlar, layklar statistikasi |
| GET | `authors/<username>/` | Muallif profili va statistikasi |

`posts/` uchun so'rov parametrlari: `search`, `category`, `tag`, `author`,
`ordering` (`created_at`, `published_at`, `views`, `likes_count`, `title`; `-` bilan teskari),
`page`, `page_size`.

Post yaratishda `category` slug ko'rinishida, `tags` esa nomlar ro'yxati sifatida yuboriladi.
`status`: `draft` yoki `published`.
