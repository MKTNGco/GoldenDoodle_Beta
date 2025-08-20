
# Database Migration Instructions

## Overview
This migration moves your invitation and user source tracking from JSON files to PostgreSQL database tables for better performance, data integrity, and concurrent access.

## Pre-Migration Checklist
1. ✅ Ensure your app is not actively being used during migration
2. ✅ Verify your database connection is working
3. ✅ Have the JSON files (`invitations.json`, `user_sources.json`) in your project root
4. ✅ Make sure you have sufficient database permissions

## Migration Process

### Step 1: Run the Migration
```bash
python migrate_json_to_database.py
```

This script will:
- Create the necessary database tables (`invitations`, `user_sources`)
- Create backup tables with timestamp suffix
- Backup existing JSON files with timestamp suffix
- Migrate all data from JSON files to database
- Verify the migration was successful

### Step 2: Monitor the Migration
- Watch the console output for any errors
- Check the `migration.log` file for detailed logs
- The script will report success/failure at the end

### Step 3: Update Your Application
After successful migration, your application will automatically use the database-based managers.

## Database Changes Made

### New Tables Created:
1. **invitations**
   - `id` (Primary Key)
   - `invite_code` (Unique)
   - `invitee_email`
   - `organization_name`
   - `invitation_type`
   - `status` (pending/accepted/expired)
   - `created_at`, `accepted_at`, `expired_at`
   - `updated_at` (auto-updated)

2. **user_sources**
   - `id` (Primary Key)
   - `user_email`
   - `signup_source`
   - `invite_code` (Foreign Key to invitations.invite_code)
   - `signup_date`, `tracked_at`

### Indexes Created:
- Performance indexes on frequently queried columns
- Foreign key relationships

### Triggers:
- Auto-update timestamp trigger for `invitations.updated_at`

## Verification Steps

After migration, verify:
```bash
# Check table existence
psql $DATABASE_URL -c "SELECT table_name FROM information_schema.tables WHERE table_name IN ('invitations', 'user_sources');"

# Check record counts
psql $DATABASE_URL -c "SELECT COUNT(*) FROM invitations;"
psql $DATABASE_URL -c "SELECT COUNT(*) FROM user_sources;"

# Check sample data
psql $DATABASE_URL -c "SELECT * FROM invitations LIMIT 5;"
psql $DATABASE_URL -c "SELECT * FROM user_sources LIMIT 5;"
```

## Rollback Instructions

### If Migration Fails
The migration script automatically attempts rollback on failure.

### Manual Rollback
If you need to rollback after successful migration:

```bash
python migrate_json_to_database.py rollback
```

This will:
1. Clear current database tables
2. Restore data from backup tables
3. Restore JSON files from timestamped backups

### Complete Rollback (Remove Tables)
If you want to completely remove the database tables and revert to JSON:

```sql
-- Remove tables
DROP TABLE IF EXISTS user_sources;
DROP TABLE IF EXISTS invitations;

-- Remove backup tables (optional)
DROP TABLE IF EXISTS invitations_backup_YYYYMMDD_HHMMSS;
DROP TABLE IF EXISTS user_sources_backup_YYYYMMDD_HHMMSS;

-- Remove the trigger function
DROP FUNCTION IF EXISTS update_updated_at_column();
```

Then restore your JSON files:
```bash
# Find and restore JSON backups
mv invitations.json.backup_YYYYMMDD_HHMMSS invitations.json
mv user_sources.json.backup_YYYYMMDD_HHMMSS user_sources.json
```

## Backup Files Created

### Database Backups:
- `invitations_backup_YYYYMMDD_HHMMSS`
- `user_sources_backup_YYYYMMDD_HHMMSS`

### JSON Backups:
- `invitations.json.backup_YYYYMMDD_HHMMSS`
- `user_sources.json.backup_YYYYMMDD_HHMMSS`

### Log Files:
- `migration.log` - Complete migration log

## Troubleshooting

### Common Issues:

1. **Database Connection Error**
   - Verify `DATABASE_URL` environment variable
   - Check database permissions

2. **JSON File Not Found**
   - Migration continues without missing files
   - Check logs for warnings

3. **Duplicate Key Errors**
   - Usually indicates existing data in tables
   - Backup tables handle this automatically

4. **Permission Denied**
   - Ensure database user has CREATE, INSERT, UPDATE, DELETE permissions

### Recovery Commands:
```bash
# View migration logs
cat migration.log

# Check backup table names
psql $DATABASE_URL -c "SELECT table_name FROM information_schema.tables WHERE table_name LIKE '%backup%';"

# Manually inspect backup data
psql $DATABASE_URL -c "SELECT COUNT(*) FROM invitations_backup_YYYYMMDD_HHMMSS;"
```

## Post-Migration Benefits

1. **Performance**: Database queries are faster than JSON file operations
2. **Concurrency**: Multiple users can access data simultaneously
3. **Data Integrity**: ACID compliance and foreign key constraints
4. **Scalability**: Better performance as data grows
5. **Querying**: Complex queries and analytics possible
6. **Backup**: Database-level backup and recovery options

## Success Indicators

✅ Migration script completes without errors
✅ All JSON data appears in database tables
✅ Record counts match between JSON and database
✅ Application functions normally after migration
✅ Backup tables and JSON files are created

If all indicators pass, your migration was successful!
