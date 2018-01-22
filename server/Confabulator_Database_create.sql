-- Created by Vertabelo (http://vertabelo.com)
-- Last modification date: 2018-01-22 15:05:18.571

-- tables
-- Table: blocked_client
CREATE TABLE blocked_client (
    blocked_client_id integer NOT NULL CONSTRAINT blocked_client_pk PRIMARY KEY AUTOINCREMENT,
    ip_address text NOT NULL,
    CONSTRAINT blocked_client_ip_address UNIQUE (ip_address)
);

-- Table: channel_ban
CREATE TABLE channel_ban (
    channel_ban_id integer NOT NULL CONSTRAINT channel_ban_pk PRIMARY KEY AUTOINCREMENT,
    communication_channel_id integer NOT NULL,
    user_account_id integer NOT NULL,
    CONSTRAINT channel_ban_cc_ua UNIQUE (communication_channel_id, user_account_id),
    CONSTRAINT channel_ban_communication_channel_id FOREIGN KEY (communication_channel_id)
    REFERENCES communication_channel (communication_channel_id),
    CONSTRAINT channel_ban_user_account_id FOREIGN KEY (user_account_id)
    REFERENCES user_account (user_account_id)
);

-- Table: channel_message
CREATE TABLE channel_message (
    channel_message_id integer NOT NULL CONSTRAINT channel_message_pk PRIMARY KEY AUTOINCREMENT,
    communication_channel_id integer NOT NULL,
    user_account_id integer NOT NULL,
    message_text text NOT NULL,
    CONSTRAINT channel_message_communication_channel_id FOREIGN KEY (communication_channel_id)
    REFERENCES communication_channel (communication_channel_id),
    CONSTRAINT channel_message_user_account_id FOREIGN KEY (user_account_id)
    REFERENCES user_account (user_account_id)
);

-- Table: channel_status
CREATE TABLE channel_status (
    channel_status_id integer NOT NULL CONSTRAINT channel_status_pk PRIMARY KEY AUTOINCREMENT,
    name text NOT NULL,
    CONSTRAINT channel_status_name UNIQUE (name)
);

-- Table: communication_channel
CREATE TABLE communication_channel (
    communication_channel_id integer NOT NULL CONSTRAINT communication_channel_pk PRIMARY KEY AUTOINCREMENT,
    name text NOT NULL,
    user_account_id integer NOT NULL,
    password_salt blob,
    password_hash blob,
    buffer_size integer NOT NULL,
    replay_size integer NOT NULL,
    channel_status_id integer NOT NULL,
    current_administrator text,
    CONSTRAINT communication_channel_name UNIQUE (name),
    CONSTRAINT communication_channel_user_account_id FOREIGN KEY (user_account_id)
    REFERENCES user_account (user_account_id),
    CONSTRAINT communication_channel_channel_status_id FOREIGN KEY (channel_status_id)
    REFERENCES channel_status (channel_status_id)
);

-- Table: global_setting
CREATE TABLE global_setting (
    global_settings_id integer NOT NULL CONSTRAINT global_setting_pk PRIMARY KEY AUTOINCREMENT,
    "key" text NOT NULL,
    value blob NOT NULL,
    CONSTRAINT global_settings_key UNIQUE ("key")
);

-- Table: inbox_message
CREATE TABLE inbox_message (
    inbox_message_id integer NOT NULL CONSTRAINT inbox_message_pk PRIMARY KEY AUTOINCREMENT,
    owner_id integer NOT NULL,
    source_id integer NOT NULL,
    message_text text NOT NULL,
    unread numeric NOT NULL,
    CONSTRAINT inbox_message_owner_id FOREIGN KEY (owner_id)
    REFERENCES user_account (user_account_id),
    CONSTRAINT inbox_message_source_id FOREIGN KEY (source_id)
    REFERENCES user_account (user_account_id)
);

-- Table: muted_user
CREATE TABLE muted_user (
    muted_user_id integer NOT NULL CONSTRAINT muted_user_pk PRIMARY KEY AUTOINCREMENT,
    communication_channel_id integer NOT NULL,
    owner_id integer NOT NULL,
    muted_id integer NOT NULL,
    CONSTRAINT muted_user_cc_owner_muted UNIQUE (communication_channel_id, owner_id, muted_id),
    CONSTRAINT muted_user_communication_channel_id FOREIGN KEY (communication_channel_id)
    REFERENCES communication_channel (communication_channel_id),
    CONSTRAINT muted_user_owner_id FOREIGN KEY (owner_id)
    REFERENCES user_account (user_account_id),
    CONSTRAINT muted_user_muted_id FOREIGN KEY (muted_id)
    REFERENCES user_account (user_account_id),
    CONSTRAINT muted_user_check CHECK (owner_id != muted_id)
);

-- Table: privilege_group
CREATE TABLE privilege_group (
    privilege_group_id integer NOT NULL CONSTRAINT privilege_group_pk PRIMARY KEY AUTOINCREMENT,
    name text NOT NULL,
    CONSTRAINT privilege_group_name UNIQUE (name)
);

-- Table: privilege_relationship
CREATE TABLE privilege_relationship (
    privilege_relationship_id integer NOT NULL CONSTRAINT privilege_relationship_pk PRIMARY KEY AUTOINCREMENT,
    parent_id integer NOT NULL,
    child_id integer NOT NULL,
    CONSTRAINT privilege_relationship_parent_child UNIQUE (parent_id, child_id),
    CONSTRAINT privilege_relationship_parent_id FOREIGN KEY (parent_id)
    REFERENCES privilege_group (privilege_group_id),
    CONSTRAINT privilege_relationship_child_id FOREIGN KEY (child_id)
    REFERENCES privilege_group (privilege_group_id),
    CONSTRAINT privilege_relationship_check CHECK (parent_id != child_id)
);

-- Table: user_account
CREATE TABLE user_account (
    user_account_id integer NOT NULL CONSTRAINT user_account_pk PRIMARY KEY AUTOINCREMENT,
    name text NOT NULL,
    online numeric NOT NULL,
    password_salt blob NOT NULL,
    password_hash blob NOT NULL,
    forgiven integer NOT NULL,
    privilege_group_id integer NOT NULL,
    CONSTRAINT user_account_name UNIQUE (name),
    CONSTRAINT user_account_privilege_group_id FOREIGN KEY (privilege_group_id)
    REFERENCES privilege_group (privilege_group_id)
);

-- Table: user_contact
CREATE TABLE user_contact (
    user_contact_id integer NOT NULL CONSTRAINT user_contact_pk PRIMARY KEY AUTOINCREMENT,
    owner_id integer NOT NULL,
    friend_id integer NOT NULL,
    CONSTRAINT user_contact_owner_friend UNIQUE (owner_id, friend_id),
    CONSTRAINT user_contact_owner_id FOREIGN KEY (owner_id)
    REFERENCES user_account (user_account_id),
    CONSTRAINT user_contact_friend_id FOREIGN KEY (friend_id)
    REFERENCES user_account (user_account_id),
    CONSTRAINT user_contact_check CHECK (owner_id != friend_id)
);

-- End of file.

