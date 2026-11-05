-- Compose 启动时由 postgres 官方镜像自动执行（只执行一次，卷为空时）
create table if not exists visits (
    id      serial primary key,
    note    text        not null default 'day173',
    created timestamptz not null default now()
);
insert into visits(note) select 'seed' where not exists (select 1 from visits);