"""
Script to clean up duplicate dependencies in the database.
Keeps the oldest dependency record and deletes duplicates.
"""

from src.database.connection import DatabaseConnection

# Connect to database
db_wrapper = DatabaseConnection()
db_conn = db_wrapper.get_connection()

print("Cleaning up duplicate dependencies...")
print("=" * 80)

# Find duplicates
cursor = db_conn.cursor()
cursor.execute("""
    SELECT blocked_task_id, blocking_task_id, COUNT(*) as count,
           GROUP_CONCAT(id) as ids
    FROM dependencies
    GROUP BY blocked_task_id, blocking_task_id
    HAVING COUNT(*) > 1
""")

duplicates = cursor.fetchall()

if not duplicates:
    print("No duplicate dependencies found!")
else:
    print(f"Found {len(duplicates)} sets of duplicate dependencies\n")

    total_deleted = 0
    for blocked_id, blocking_id, count, ids_str in duplicates:
        ids = [int(x) for x in ids_str.split(',')]
        keep_id = min(ids)  # Keep the oldest (smallest ID)
        delete_ids = [x for x in ids if x != keep_id]

        print(f"Blocked Task {blocked_id} -> Blocking Task {blocking_id}:")
        print(f"  Found {count} records with IDs: {ids}")
        print(f"  Keeping ID {keep_id}, deleting {delete_ids}")

        # Delete duplicates
        for del_id in delete_ids:
            cursor.execute("DELETE FROM dependencies WHERE id = ?", (del_id,))
            total_deleted += 1

    db_conn.commit()
    print(f"\n" + "=" * 80)
    print(f"Cleanup complete! Deleted {total_deleted} duplicate dependency records.")

print("\nVerifying cleanup...")
cursor.execute("""
    SELECT COUNT(*)
    FROM dependencies
    GROUP BY blocked_task_id, blocking_task_id
    HAVING COUNT(*) > 1
""")

remaining_duplicates = cursor.fetchone()
if remaining_duplicates:
    print(f"WARNING: Still have duplicates!")
else:
    print("Success! No duplicate dependencies remain.")
