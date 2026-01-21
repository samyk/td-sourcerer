// License: MIT
// Sourcerer Lite - Transitions shader
// Transitions: Dissolve, Dip, Slide, Wipe, Blur, File, Top

uniform float progress;  // Always 0 to 1
uniform int mode;
uniform int state;  // 0 = transitioning from input0 to input1, 1 = transitioning from input1 to input0

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

// State-aware blur sample
vec4 blurSampleOutgoing(vec2 uv, float radius) {
	int inputIdx = (state == 0) ? 0 : 1;
	vec2 texelSize = 1.0 / uTD2DInfos[inputIdx].res.zw;
	vec4 color = vec4(0.0);

	// 9-tap box blur
	for (int x = -1; x <= 1; x++) {
		for (int y = -1; y <= 1; y++) {
			vec2 offset = vec2(float(x), float(y)) * texelSize * radius;
			color += getOutgoing(uv + offset);
		}
	}
	return color / 9.0;
}

vec4 blurSampleIncoming(vec2 uv, float radius) {
	int inputIdx = (state == 0) ? 1 : 0;
	vec2 texelSize = 1.0 / uTD2DInfos[inputIdx].res.zw;
	vec4 color = vec4(0.0);

	// 9-tap box blur
	for (int x = -1; x <= 1; x++) {
		for (int y = -1; y <= 1; y++) {
			vec2 offset = vec2(float(x), float(y)) * texelSize * radius;
			color += getIncoming(uv + offset);
		}
	}
	return color / 9.0;
}


// TRANSITIONS

// Dissolve - simple crossfade
vec4 Dissolve(vec2 uv)
{
	return mix(getOutgoing(uv), getIncoming(uv), progress);
}

// Dip - fade to color then from color (no source mixing)
vec4 Dip(vec2 uv)
{
	if (progress < 0.5) {
		// First half: fade from outgoing to dip_color
		// Remap progress 0.0-0.5 to 0.0-1.0
		float t = progress * 2.0;
		return mix(getOutgoing(uv), dip_color, t);
	}
	else {
		// Second half: fade from dip_color to incoming
		// Remap progress 0.5-1.0 to 0.0-1.0
		float t = (progress - 0.5) * 2.0;
		return mix(dip_color, getIncoming(uv), t);
	}
}

// Slide - content pushes in/out
vec4 Slide(vec2 uv)
{
	float x = progress * trans_direction.x;
	float y = progress * trans_direction.y;

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
	// Calculate wipe threshold based on direction
	// For horizontal wipe (direction.x != 0): compare uv.x
	// For vertical wipe (direction.y != 0): compare uv.y
	float threshold = progress;
	float coord;

	if (abs(trans_direction.x) > abs(trans_direction.y)) {
		// Horizontal wipe
		coord = (trans_direction.x > 0.0) ? uv.x : (1.0 - uv.x);
	}
	else {
		// Vertical wipe
		coord = (trans_direction.y > 0.0) ? uv.y : (1.0 - uv.y);
	}

	// Hard edge: incoming revealed where coord < threshold
	if (coord < threshold) {
		return getIncoming(uv);
	}
	else {
		return getOutgoing(uv);
	}
}

// Blur - crossfade with blur peaking at midpoint
vec4 Blur(vec2 uv)
{
	// Maximum blur radius at midpoint
	float maxRadius = 6.0;

	// Blur amount: 0 at ends, max at middle
	float blurAmount = (1.0 - abs(progress * 2.0 - 1.0)) * maxRadius;

	// Sample both sources with blur
	vec4 colorOut, colorIn;
	if (blurAmount < 0.5) {
		// No blur needed
		colorOut = getOutgoing(uv);
		colorIn = getIncoming(uv);
	}
	else {
		colorOut = blurSampleOutgoing(uv, blurAmount);
		colorIn = blurSampleIncoming(uv, blurAmount);
	}

	// Crossfade between blurred sources
	return mix(colorOut, colorIn, progress);
}

// Luma matte transition helper
// Matte goes black to white - black pixels transition first
vec4 LumaMatte(vec2 uv, float luma)
{
	// Where luma < progress, show incoming; otherwise show outgoing
	// Black (0) transitions first, white (1) transitions last
	if (luma < progress) {
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
