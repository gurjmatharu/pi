# Tasks
- [x] Setup Supabase
- [x] Set up database structure and add openai
- [x] fastapi backend with supabase backend/orm
- [ ] Turn off Application (https://one.dash.cloudflare.com/3ce5ba63ac28ef43d0e610e064a10167/access/policies?tab=reusable) to enable admin ui
- [ ] set up backend with fastapi and openai

# Setup

This project uses cloudflare for all networking.

Dev machine -> Cloudflare -> RaspberryPI

We develop on main, we're always live :D

# FastAPI

```
cd fastapi
uvicorn main:app --reload --host 0.0.0.0 --port 8001
```


To see Tunnel Health:
- [Tunnel Config](https://one.dash.cloudflare.com/3ce5ba63ac28ef43d0e610e064a10167/networks/tunnels/cfd_tunnel/d8886c20-1fdb-4102-8b08-b214aa171870/edit?tab=overview)
- Access Applications - how to turn off auth 
- [Domains](https://one.dash.cloudflare.com/3ce5ba63ac28ef43d0e610e064a10167/networks/tunnels/cfd_tunnel/d8886c20-1fdb-4102-8b08-b214aa171870/edit?tab=publicHostname)
- [Supabase Docs](https://supabase.com/docs/guides/local-development/overview)

## Database Migrations

- make sure [supabase cli](https://supabase.com/docs/guides/local-development/cli/getting-started?queryGroups=platform&platform=linux) is installed
- [migrations](https://supabase.com/docs/guides/local-development/overview)

```
supabase migration new create_employees_table
supabase db push --db-url "postgres://postgres:your-super-secret-and-long-postgres-password@localhost:5432/postgres"
```
