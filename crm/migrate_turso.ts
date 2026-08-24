import { createClient } from '@libsql/client';
import { Database } from 'bun:sqlite';

const localDb = new Database('../leads.db');

if (!process.env.DATABASE_URL || !process.env.DATABASE_AUTH_TOKEN) {
    console.error("Missing DATABASE_URL or DATABASE_AUTH_TOKEN in .env");
    process.exit(1);
}

const tursoDb = createClient({
    url: process.env.DATABASE_URL,
    authToken: process.env.DATABASE_AUTH_TOKEN
});

async function migrate() {
    console.log('Creating schema on Turso...');
    await tursoDb.execute(`
        CREATE TABLE IF NOT EXISTS leads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            stage TEXT,
            business TEXT,
            website TEXT,
            phone TEXT,
            email TEXT,
            status TEXT,
            remarks TEXT,
            idea_url TEXT,
            date TEXT
        )
    `);

    // Clean existing just in case we re-run
    await tursoDb.execute('DELETE FROM leads');

    const leads = localDb.query('SELECT * FROM leads').all();
    console.log(`Migrating ${leads.length} leads to Turso...`);

    let count = 0;
    for (const lead of leads as any[]) {
        await tursoDb.execute({
            sql: 'INSERT INTO leads (id, stage, business, website, phone, email, status, remarks, idea_url, date) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
            args: [
                lead.id, 
                lead.stage || 'main', 
                lead.business || '', 
                lead.website || '', 
                lead.phone || '', 
                lead.email || '', 
                lead.status || 'New', 
                lead.remarks || '', 
                lead.idea_url || '', 
                lead.date || ''
            ]
        });
        count++;
    }

    console.log(`Successfully migrated ${count} leads!`);
}

migrate().catch(console.error);
