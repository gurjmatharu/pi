// Follow this setup guide to integrate the Deno language server with your editor:
// https://deno.land/manual/getting_started/setup_your_environment
// This enables autocomplete, go to definition, etc.

// Setup type definitions for built-in Supabase Runtime APIs
import "jsr:@supabase/functions-js/edge-runtime.d.ts"
import { createClient } from "npm:@supabase/supabase-js@2.39.5";

interface RequestPayload {
	user_id: number;
	image_base64: string;
	food_log_id?: number;
}

const supabase = createClient(
	Deno.env.get("SUPABASE_URL")!,
	Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!
);

console.info("📦 log-food function ready");

Deno.serve(async (req: Request) => {
	if (req.method !== "POST") {
		return new Response("Method Not Allowed", { status: 405 });
	}

	try {
		const { user_id, image_base64, food_log_id }: RequestPayload = await req.json();

		const fileName = `${crypto.randomUUID()}.jpg`;
		const filePath = `food_logs/${user_id}/${fileName}`;
		const binaryImage = decodeBase64(image_base64);

		// Upload image to storage
		const { error: uploadError } = await supabase.storage
			.from("food-photos")
			.upload(filePath, binaryImage, {
				contentType: "image/jpeg"
			});

		if (uploadError) throw uploadError;

		const { data: publicUrlData } = supabase.storage
			.from("food-photos")
			.getPublicUrl(filePath);

		const newImageUrl = publicUrlData.publicUrl;
		let updatedImageUrls: string[] = [newImageUrl];

		if (food_log_id) {
			// Update existing food log
			const { data: existing, error: fetchError } = await supabase
				.from("food_log")
				.select("image_urls")
				.eq("id", food_log_id)
				.single();

			if (fetchError) throw fetchError;

			if (existing?.image_urls?.length) {
				updatedImageUrls = [...existing.image_urls, newImageUrl];
			}

			const { error: updateError } = await supabase
				.from("food_log")
				.update({ image_urls: updatedImageUrls })
				.eq("id", food_log_id);

			if (updateError) throw updateError;
		} else {
			// Insert new food log entry
			const { error: insertError } = await supabase
				.from("food_log")
				.insert({
					user_id,
					image_urls: updatedImageUrls
				});

			if (insertError) throw insertError;
		}

		return new Response(
			JSON.stringify({
				success: true,
				image_url: newImageUrl,
				food_log_id: food_log_id ?? null
			}),
			{
				headers: {
					"Content-Type": "application/json",
					"Connection": "keep-alive"
				}
			}
		);
	} catch (err) {
		console.error("❌ Error:", err);
		return new Response(
			JSON.stringify({ error: err.message ?? "Internal Server Error" }),
			{ status: 500, headers: { "Content-Type": "application/json" } }
		);
	}
});

// Utility
function decodeBase64(b64: string): Uint8Array {
	return Uint8Array.from(atob(b64), c => c.charCodeAt(0));
}

/* To invoke locally:

  1. Run `supabase start` (see: https://supabase.com/docs/reference/cli/supabase-start)
  2. Make an HTTP request:

  curl -i --location --request POST 'http://127.0.0.1:54321/functions/v1/log-food' \
    --header 'Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZS1kZW1vIiwicm9sZSI6ImFub24iLCJleHAiOjE5ODM4MTI5OTZ9.CRXP1A7WOeoJeXxjNni43kdQwgnWNReilDMblYTn_I0' \
    --header 'Content-Type: application/json' \
    --data '{"name":"Functions"}'

*/
