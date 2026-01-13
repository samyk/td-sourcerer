// License: MIT
// Sourcerer Lite - Minimal transitions shader
// Bidirectional transitions: Fade, Fade Color, Slide

uniform float progress;
uniform int mode;
uniform int state;  // 0 = transitioning from input0, 1 = transitioning from input1

// FadeColor
uniform vec4 fade_color;

// Slide
uniform vec2 slide_trans;


// HELPER FUNCTIONS

// Fixed input accessors
vec4 getInput0(vec2 uv) { return texture(sTD2DInputs[0], uv); }
vec4 getInput1(vec2 uv) { return texture(sTD2DInputs[1], uv); }

// State-aware accessors: outgoing = sliding away, incoming = sliding in
vec4 getOutgoing(vec2 uv) {
	return (state == 0) ? getInput0(uv) : getInput1(uv);
}

vec4 getIncoming(vec2 uv) {
	return (state == 0) ? getInput1(uv) : getInput0(uv);
}


// TRANSITIONS

// Fade - simple crossfade, works bidirectionally with progress
vec4 Fade(vec2 uv)
{
	return mix(getInput0(uv), getInput1(uv), progress);
}

// Fade Color - symmetric fade through a color at midpoint
vec4 FadeColor(vec2 uv)
{
	// Distance from endpoints: 0 at ends (progress=0 or 1), 1 at middle (progress=0.5)
	float mid_blend = 1.0 - abs(progress * 2.0 - 1.0);

	// Blend between inputs based on progress
	vec4 endpoint_color = mix(getInput0(uv), getInput1(uv), progress);

	// Mix with fade_color at midpoint
	return mix(endpoint_color, fade_color, mid_blend);
}

// Slide - bidirectional, outgoing always slides in direction of slide_trans
vec4 Slide(vec2 uv)
{
	// Normalize progress to 0->1 for transition math (outgoing slides out)
	float t = (state == 0) ? progress : (1.0 - progress);

	float x = t * slide_trans.x;
	float y = t * slide_trans.y;

	if (x >= 0.0 && y >= 0.0) {
		// Sliding right and/or up
		if (uv.x >= x && uv.y >= y) {
			// In outgoing region
			return getOutgoing(uv - vec2(x, y));
		}
		else {
			// In incoming region
			vec2 iuv;
			if (x > 0.0)
				iuv = vec2(x - 1.0, y);
			else if (y > 0.0)
				iuv = vec2(x, y - 1.0);
			return getIncoming(uv - iuv);
		}
	}
	else if (x <= 0.0 && y <= 0.0) {
		// Sliding left and/or down
		if (uv.x <= (1.0 + x) && uv.y <= (1.0 + y)) {
			// In outgoing region
			return getOutgoing(uv - vec2(x, y));
		}
		else {
			// In incoming region
			vec2 iuv;
			if (x < 0.0)
				iuv = vec2(x + 1.0, y);
			else if (y < 0.0)
				iuv = vec2(x, y + 1.0);
			return getIncoming(uv - iuv);
		}
	}
	else {
		return vec4(0.0);
	}
}


layout(location = 0) out vec4 fragColor;
void main() {
	vec4 o = vec4(0.0, 0.0, 0.0, 0.0);

	switch(mode) {
		case 0: o = Fade(vUV.st); break;
		case 1: o = FadeColor(vUV.st); break;
		case 2: o = Slide(vUV.st); break;
	}

	fragColor = TDOutputSwizzle(o);
}
