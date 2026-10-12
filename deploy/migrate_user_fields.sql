-- Add optional contact fields to existing videoportal.users
ALTER TABLE users
  ADD COLUMN IF NOT EXISTS mobile_no VARCHAR(64) NULL AFTER role,
  ADD COLUMN IF NOT EXISTS id_card_no VARCHAR(128) NULL AFTER mobile_no;
