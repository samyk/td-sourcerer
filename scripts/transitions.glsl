// License: MIT
// Sourcerer Lite - Transitions shader
// Transitions: Dissolve, Dip, Slide, Wipe, Blur, File, Top

uniform float progress;
uniform int mode;
uniform int state;  // 0 = transitioning from input0, 1 = transitioning from input1

// Dip to color
uniform vec4 dip_color;

// Slide/Wipe direction
uniform vec2 trans_direction;


// HELPER FUNCTIONS

// Fixed input accessors
vec4 getInput0(vec2 uv) { return texture(sTD2DInputs[0], uv); }
vec4 getInput1(vec2 uv) { return texture(sTD2DInputs[1], uv); }

// Transition matte accessors (black to white gradient images)
vec4 getTransFile(vec2 uv) { return texture(sTD2DInputs[2], uv); }
vec4 getTransTop(vec2 uv) { return texture(sTD2DInputs[3], uv); }

// State-aware accessors: outgoing = leaving, incoming = entering
vec4 getOutgoing(vec2 uv) {
	return (state == 0) ? getInput0(uv) : getInput1(uv);
}

vec4 getIncoming(vec2 uv) {
	return (state == 0) ? getInput1(uv) : getInput0(uv);
}

// Simple blur sample - samples in a cross pattern
vec4 blurSample(int inputIdx, vec2 uv, float radius) {
	vec2 texelSize = 1.0 / uTD2DInfos[inputIdx].res.zw;
	vec4 color = vec4(0.0);

	// 9-tap box blur
	for (int x = -1; x <= 1; x++) {
		for (int y = -1; y <= 1; y++) {
			vec2 offset = vec2(float(x), float(y)) * texelSize * radius;
			if (inputIdx == 0)
				color += getInput0(uv + offset);
			else
				color += getInput1(uv + offset);
		}
	}
	return color / 9.0;
}


// TRANSITIONS

// Dissolve - simple crossfade
vec4 Dissolve(vec2 uv)
{
	return mix(getInput0(uv), getInput1(uv), progress);
}

// Dip - fade through a color at midpoint
vec4 Dip(vec2 uv)
{
	// Distance from endpoints: 0 at ends, 1 at middle (progress=0.5)
	float mid_blend = 1.0 - abs(progress * 2.0 - 1.0);

	// Blend between inputs based on progress
	vec4 endpoint_color = mix(getInput0(uv), getInput1(uv), progress);

	// Mix with dip_color at midpoint
	return mix(endpoint_color, dip_color, mid_blend);
}

// Slide - content pushes in/out
vec4 Slide(vec2 uv)
{
	// Normalize progress for transition math
	float t = (state == 0) ? progress : (1.0 - progress);

	float x = t * trans_direction.x;
	float y = t * trans_direction.y;

	if (x >= 0.0 && y >= 0.0) {
		// Sliding right and/or up
		if (uv.x >= x && uv.y >= y) {
			return getOutgoing(uv - vec2(x, y));
		}
		else {
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
			return getOutgoing(uv - vec2(x, y));
		}
		else {
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

// Wipe - hard edge reveal
vec4 Wipe(vec2 uv)
{
	// Normalize progress for transition math
	float t = (state == 0) ? progress : (1.0 - progress);

	// Calculate wipe threshold based on direction
	// For horizontal wipe (direction.x != 0): compare uv.x
	// For vertical wipe (direction.y != 0): compare uv.y
	float threshold;
	float coord;

	if (abs(trans_direction.x) > abs(trans_direction.y)) {
		// Horizontal wipe
		coord = (trans_direction.x > 0.0) ? uv.x : (1.0 - uv.x);
		threshold = t;
	}
	else {
		// Vertical wipe
		coord = (trans_direction.y > 0.0) ? uv.y : (1.0 - uv.y);
		threshold = t;
	}

	// Hard edge: incoming revealed where coord < threshold
	if (coord < threshold) {
		return getIncoming(uv);
	}
	else {
		return getOutgoing(uv);
	}
}

// Blur - blur out then blur in
vec4 Blur(vec2 uv)
{
	// Maximum blur radius at midpoint
	float maxRadius = 20.0;

	// Blur amount: 0 at ends, max at middle
	float blurAmount = (1.0 - abs(progress * 2.0 - 1.0)) * maxRadius;

	if (progress < 0.5) {
		// First half: blur outgoing
		if (blurAmount < 0.5) {
			return getOutgoing(uv);
		}
		return blurSample(state, uv, blurAmount);
	}
	else {
		// Second half: unblur incoming
		int incomingIdx = 1 - state;
		if (blurAmount < 0.5) {
			return getIncoming(uv);
		}
		return blurSample(incomingIdx, uv, blurAmount);
	}
}

// Luma matte transition helper
// Matte goes black to white - black pixels transition first
vec4 LumaMatte(vec2 uv, float luma)
{
	// Adjust progress based on state direction
	float t = (state == 0) ? progress : (1.0 - progress);

	// Where luma < progress, show incoming; otherwise show outgoing
	// Black (0) transitions first, white (1) transitions last
	if (luma < t) {
		return getIncoming(uv);
	}
	else {
		return getOutgoing(uv);
	}
}

// File - luma matte transition from file texture (input 2)
vec4 TransFile(vec2 uv)
{
	// Sample the transition matte and get luminance
	vec4 matte = getTransFile(uv);
	float luma = dot(matte.rgb, vec3(0.299, 0.587, 0.114));
	return LumaMatte(uv, luma);
}

// Top - luma matte transition from TOP texture (input 3)
vec4 TransTop(vec2 uv)
{
	// Sample the transition matte and get luminance
	vec4 matte = getTransTop(uv);
	float luma = dot(matte.rgb, vec3(0.299, 0.587, 0.114));
	return LumaMatte(uv, luma);
}


layout(location = 0) out vec4 fragColor;
void main() {
	vec4 o = vec4(0.0, 0.0, 0.0, 0.0);

	switch(mode) {
		case 0: o = Dissolve(vUV.st); break;
		case 1: o = Dip(vUV.st); break;
		case 2: o = Slide(vUV.st); break;
		case 3: o = Wipe(vUV.st); break;
		case 4: o = Blur(vUV.st); break;
		case 5: o = TransFile(vUV.st); break;
		case 6: o = TransTop(vUV.st); break;
	}

	fragColor = TDOutputSwizzle(o);
}
