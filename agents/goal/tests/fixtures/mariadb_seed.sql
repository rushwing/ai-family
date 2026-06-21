-- TC-003-01 MariaDB→PG16 搬迁 fixture（脱敏）。
-- 覆盖核心实体链，按两个成员分区（best_pal/go_getter A、B），
-- 用于校验搬迁后的字段/关联/计数与跨成员归属（family_member_id 映射）。
-- 列名/枚举/NOT NULL 取自 agents/goal/app/models（004 重命名后表名）。
-- 幂等：每次先清空再插入。

SET FOREIGN_KEY_CHECKS = 0;
TRUNCATE TABLE check_ins;
TRUNCATE TABLE tasks;
TRUNCATE TABLE weekly_milestones;
TRUNCATE TABLE plans;
TRUNCATE TABLE targets;
TRUNCATE TABLE reports;
TRUNCATE TABLE go_getters;
TRUNCATE TABLE best_pals;
SET FOREIGN_KEY_CHECKS = 1;

-- 成员 A / B 的家长
INSERT INTO best_pals (id, name, telegram_chat_id, is_admin) VALUES
  (1, 'parent-A', 1001, 1),
  (2, 'parent-B', 1002, 0);

-- 各自一名 go_getter
INSERT INTO go_getters (id, best_pal_id, name, display_name, grade, telegram_chat_id,
                        xp_total, streak_current, streak_longest) VALUES
  (1, 1, 'kid-A', 'Kid A', 'G3', 2001, 1250, 7, 14),
  (2, 2, 'kid-B', 'Kid B', 'G4', 2002, 880, 3, 9);

-- vacation_type 为 Enum NOT NULL 无默认（alembic 001），必填。
INSERT INTO targets (id, go_getter_id, title, subject, description, vacation_type, vacation_year, priority, status) VALUES
  (1, 1, 'Math Mastery A', 'math', 'desc A', 'summer', 2026, 1, 'active'),
  (2, 2, 'Reading Habit B', 'reading', 'desc B', 'winter', 2026, 1, 'active');

INSERT INTO plans (id, target_id, title, overview, start_date, end_date, total_weeks, status) VALUES
  (1, 1, 'Plan A', 'overview A', '2026-01-01', '2026-03-01', 8, 'active'),
  (2, 2, 'Plan B', 'overview B', '2026-01-01', '2026-03-01', 8, 'active');

INSERT INTO weekly_milestones (id, plan_id, week_number, title, description, start_date, end_date) VALUES
  (1, 1, 1, 'Week 1 A', 'wk desc A', '2026-01-01', '2026-01-07'),
  (2, 2, 1, 'Week 1 B', 'wk desc B', '2026-01-01', '2026-01-07');

INSERT INTO tasks (id, milestone_id, day_of_week, sequence_in_day, title, description, task_type, status) VALUES
  (1, 1, 1, 1, 'Task A', 'task desc A', 'practice', 'active'),
  (2, 2, 1, 1, 'Task B', 'task desc B', 'reading', 'active');

INSERT INTO check_ins (id, task_id, go_getter_id, status, xp_earned, streak_at_checkin,
                       duration_minutes, notes) VALUES
  (1, 1, 1, 'completed', 10, 7, 35, 'done A'),
  (2, 2, 2, 'completed', 10, 3, 20, 'done B');

INSERT INTO reports (id, go_getter_id, report_type, period_start, period_end, content_md) VALUES
  (1, 1, 'weekly', '2026-01-01', '2026-01-07', 'report A'),
  (2, 2, 'weekly', '2026-01-01', '2026-01-07', 'report B');
