# How to get it up and running
- Install and run cloudflared locally to make sure it works see new cloudflare docs: sudo cloudflared service install <YOUR TOKEN>
- CONNECT DNS TO TUNNEL: `cloudflared tunnel route dns gurj-tunnel n8n.gurj.ai`
- DONE
- https://github.com/supabase/supabase/issues/30640 run supabase on raspberry pi 

TODO:
- Fix port mapping issue CLOUDFLARE > DOCKER NETWORK NOT LOCALHOST
