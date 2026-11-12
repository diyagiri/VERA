import {sqliteTable,text,integer} from 'drizzle-orm/sqlite-core';
export const sessions=sqliteTable('vera_sessions',{id:text('id').primaryKey(),payload:text('payload').notNull(),expires:integer('expires').notNull(),revision:integer('revision').notNull().default(0),lockedUntil:integer('locked_until').notNull().default(0)});
export const counters=sqliteTable('vera_counters',{id:text('id').primaryKey(),requests:integer('requests').notNull().default(0),tokens:integer('tokens').notNull().default(0),expires:integer('expires').notNull()});
export const config=sqliteTable('vera_config',{id:text('id').primaryKey(),value:text('value').notNull()});
export const vectors=sqliteTable('vera_vectors',{id:text('id').primaryKey(),corpus:text('corpus').notNull(),model:text('model').notNull(),vector:text('vector').notNull()});
