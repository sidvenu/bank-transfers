drop table if exists transactions;
drop table if exists balances;

create table transactions (
    id char(36) primary key,
    amount int not null,
    account_no char(12) not null,
    initiate_ts int unsigned not null,
    complete_ts int unsigned not null
);
create table balances (
    account_no char(12) primary key,
    balance int not null
);

insert into balances(account_no, balance)
values
    ('123456789012', 50000),
    ('098765432145', 1000000),
    ('098765432147', 1000000),
    ('876569943818', 2958700),
    ('147140465986', 329250);
