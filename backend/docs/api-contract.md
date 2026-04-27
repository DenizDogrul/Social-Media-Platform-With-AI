# API Contract (v1)

## Auth / Users
- POST /users/register
  - req: { username, email, password }
  - 201: { id, username, email }
  - 400: { detail }

- POST /users/login
  - req: { username, password }
  - 200: { access_token, refresh_token, token_type }

- POST /users/refresh
  - req: { refresh_token }
  - 200: { access_token, refresh_token, token_type }
  - 401: { detail }

- POST /users/logout
  - req: { refresh_token }
  - 200: { message }

- GET /users/me
  - 200: { id, username, email }
  - 401: { detail }

- GET /users/{user_id}
  - 200: { id, username, email, followers_count, following_count, posts_count, is_following, is_me }
  - 404: { detail }

- GET /users/discover/follow-suggestions
  - 200: [{ id, username, email }]

## Posts / Likes
- POST /posts
- POST /posts/upload-media
- PATCH /posts/{post_id}
- DELETE /posts/{post_id}
- GET /posts/feed
- GET /posts/explore
- GET /posts/user/{user_id}
- GET /posts/{post_id}
- POST /posts/{post_id}/like
- POST /posts/{post_id}/unlike
- POST /posts/{post_id}/bookmark
- DELETE /posts/{post_id}/bookmark
- GET /posts/bookmarks/list
- GET /posts/{post_id}/likes

## Notifications
- GET /notifications
- POST /notifications/{notification_id}/read
- POST /notifications/read-all
- WS /ws/notifications?token={access_token}

## Comments
- POST /comments/posts/{post_id}
  - req: { content }
  - 201: { id, content, user_id, post_id, created_at }

- GET /comments/posts/{post_id}
  - 200: [Comment]

- DELETE /comments/{comment_id}
  - 200: { message }
  - 403/404: { detail }

## Messages
- POST /messages/conversations/{other_user_id}
  - 201: { id, user1_id, user2_id }

- GET /messages/conversations
  - 200: [Conversation]

- POST /messages/conversations/{conversation_id}/messages
  - req: { content }
  - 201: { id, conversation_id, sender_id, content, created_at }

- GET /messages/conversations/{conversation_id}/messages
  - 200: [Message]