<?php
return [
  'db_host' => getenv('HORDE_AUTH_DB_HOST') ?: 'localhost',
  'db_name' => getenv('HORDE_AUTH_DB_NAME') ?: 'hm549713_horde',
  'db_user' => getenv('HORDE_AUTH_DB_USER') ?: 'hm549713_horde',
  'db_password' => getenv('HORDE_AUTH_DB_PASSWORD') ?: '',
  'server_secret' => getenv('HORDE_AUTH_SERVER_SECRET') ?: '',
  'cors_origins' => ['https://hordeminecraft.ru', 'https://www.hordeminecraft.ru'],
  'session_days' => 30,
];
