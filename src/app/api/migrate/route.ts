import { NextRequest, NextResponse } from "next/server";
import { sql } from "drizzle-orm";
import { db } from "@/db";

export async function GET(req: NextRequest) {
  if (req.headers.get("x-migrate-secret") !== "pagescore2024") {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  const results: string[] = [];

  try {
    // reports
    await db.execute(sql`
      CREATE TABLE IF NOT EXISTS "reports" (
        "id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
        "email" text NOT NULL,
        "url" text NOT NULL,
        "score" integer NOT NULL,
        "summary" text,
        "tips" jsonb,
        "categories" jsonb,
        "product_price" numeric,
        "product_category" text,
        "estimated_visitors" integer,
        "created_at" timestamp DEFAULT now()
      )
    `);
    results.push("reports: ok");

    // subscribers
    await db.execute(sql`
      CREATE TABLE IF NOT EXISTS "subscribers" (
        "id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
        "email" text NOT NULL,
        "first_scan_url" text,
        "first_scan_score" integer,
        "created_at" timestamp DEFAULT now(),
        CONSTRAINT "subscribers_email_unique" UNIQUE("email")
      )
    `);
    results.push("subscribers: ok");

    // scans
    await db.execute(sql`
      CREATE TABLE IF NOT EXISTS "scans" (
        "id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
        "url" text NOT NULL,
        "score" integer,
        "product_category" text,
        "product_price" numeric,
        "created_at" timestamp DEFAULT now()
      )
    `);
    results.push("scans: ok");

    // stores
    await db.execute(sql`
      CREATE TABLE IF NOT EXISTS "stores" (
        "id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
        "domain" text NOT NULL,
        "name" text,
        "created_at" timestamp DEFAULT now(),
        "updated_at" timestamp DEFAULT now(),
        CONSTRAINT "stores_domain_unique" UNIQUE("domain")
      )
    `);
    results.push("stores: ok");

    // store_products
    await db.execute(sql`
      CREATE TABLE IF NOT EXISTS "store_products" (
        "id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
        "store_id" uuid NOT NULL,
        "url" text NOT NULL,
        "slug" text NOT NULL,
        "image" text,
        "created_at" timestamp DEFAULT now(),
        CONSTRAINT "store_products_store_id_url_unique" UNIQUE("store_id","url")
      )
    `);
    results.push("store_products: ok");

    // store_products FK (ignore if already exists)
    try {
      await db.execute(sql`
        ALTER TABLE "store_products"
        ADD CONSTRAINT "store_products_store_id_stores_id_fk"
        FOREIGN KEY ("store_id") REFERENCES "public"."stores"("id")
        ON DELETE no action ON UPDATE no action
      `);
      results.push("store_products FK: created");
    } catch {
      results.push("store_products FK: already exists");
    }

    // product_analyses
    await db.execute(sql`
      CREATE TABLE IF NOT EXISTS "product_analyses" (
        "id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
        "product_url" text NOT NULL,
        "store_domain" text NOT NULL,
        "score" integer NOT NULL,
        "summary" text,
        "tips" jsonb,
        "categories" jsonb,
        "product_price" numeric,
        "product_category" text,
        "estimated_monthly_visitors" integer,
        "created_at" timestamp DEFAULT now(),
        "updated_at" timestamp DEFAULT now(),
        CONSTRAINT "product_analyses_product_url_unique" UNIQUE("product_url")
      )
    `);
    results.push("product_analyses: ok");

    return NextResponse.json({ success: true, tables: results });
  } catch (error) {
    console.error("[migrate] Migration failed:", error);
    return NextResponse.json(
      { error: "Migration failed", details: String(error), completed: results },
      { status: 500 }
    );
  }
}
