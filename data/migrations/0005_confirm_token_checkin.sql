-- 0005_confirm_token_checkin —— REQ-003 WP-7：Draft-First 打卡两段式确认（kid 红线，BUG-018）。
-- confirm_token（0002 建表，已 RLS）补：task 绑定 + 一次性消费标记。
-- kid 打卡须 prepare（发 token，不写）→ confirm/submit（凭 token 写，并消费）；无有效 token 不得写。
-- 幂等可重复执行。

ALTER TABLE confirm_token ADD COLUMN IF NOT EXISTS task_id bigint;
ALTER TABLE confirm_token ADD COLUMN IF NOT EXISTS consumed_at timestamptz;
