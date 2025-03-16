-- users table
CREATE TABLE IF NOT EXISTS users (
    user_id bigint NOT NULL PRIMARY KEY,
    username varchar(255) NOT NULL,
    login_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP WITHOUT TIME ZONE
);

--  users_channels table
CREATE TABLE IF NOT EXISTS user_channels (
    channel_id bigint NOT NULL PRIMARY KEY,
    user_id bigint NOT NULL REFERENCES users(user_id),
    channel_name varchar(255) NOT NULL,
    channel_topic text NULL default '',
    channel_link varchar(255) NULL,
    addition_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP WITHOUT TIME ZONE,
    is_active boolean NOT NULL default true
);

-- channels_news table
CREATE TABLE IF NOT EXISTS channels_news (
    news_id bigint NOT NULL PRIMARY KEY,
    channel_id bigint NOT NULL REFERENCES user_channels(channel_id),
    news varchar(255) NOT NULL,
    addition_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP WITHOUT TIME ZONE
);

-- digests table
CREATE TABLE IF NOT EXISTS digests (
    digest_id bigint NOT NULL PRIMARY KEY,
    user_id bigint NOT NULL REFERENCES users(user_id),
    digest_content varchar(255) NOT NULL,
    creation_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP WITHOUT TIME ZONE
);