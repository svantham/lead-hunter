import { createClient } from '@libsql/client';
import { env } from '$env/dynamic/private';
import path from 'path';

// If deployed on Vercel, this should point to a remote Turso DB. 
// Locally, it uses the local file.
const url = env.DATABASE_URL || `file:${path.resolve('../leads.db')}`;

export const db = createClient({
    url: url,
    authToken: env.DATABASE_AUTH_TOKEN
});

export type Lead = {
    id: number;
    stage: 'main' | 'call';
    business: string;
    website: string;
    phone: string;
    email: string;
    status: string;
    remarks: string;
    idea_url: string;
    date: string;
};
