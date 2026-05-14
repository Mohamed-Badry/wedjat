#version 300 es
precision highp float;

// =================================================================
// 1. SHARED UNIFORMS & UTILS
// =================================================================

uniform vec2 u_resolution;
uniform vec2 u_mouse;
uniform float u_time;
uniform float u_opacity;
uniform float u_scale;
uniform float u_max_dist;
uniform float u_beam_width;

// Colors
uniform vec3 u_beam_color;
uniform vec3 u_color_off;
uniform vec3 u_color_on;

// Geometry Config
uniform float u_dish_radius;
uniform float u_dish_width;
uniform float u_rod_length;
uniform float u_rod_width;
uniform float u_tip_size;

// Signal Config
uniform float u_signal_speed;
uniform float u_signal_amp;
uniform float u_signal_freq;
uniform float u_signal_packet_freq;
uniform float u_signal_packet_speed;
uniform float u_signal_width;
uniform float u_signal_fade_scale;
uniform float u_antenna_fade_scale;

float hash(vec2 p) {
    return fract(sin(dot(p, vec2(12.9898, 78.233))) * 43758.5453);
}

// =================================================================
// 2. VERTEX SHADER
// =================================================================
#ifdef VERTEX_SHADER

// Per-Vertex Attributes
layout(location = 0) in vec2 a_pos;    // Quad vertex position (-0.5 to 0.5)

// Per-Instance Attributes
layout(location = 1) in vec2 a_gridPos; // Center position of this antenna

// Outputs to Fragment Shader
out vec2 v_local_pos;
out float v_dist_to_mouse;
out float v_opacity_factor;
out float v_random_val;

void main() {
    vec2 grid_pos = a_gridPos;
    
    // Correct mouse coordinate for GL (Bottom-Left origin)
    vec2 mouse_gl = vec2(u_mouse.x, u_resolution.y - u_mouse.y);
    
    vec2 delta = mouse_gl - grid_pos;
    float dist = length(delta);
    
    // Hard Cull (Move off-screen if too far)
    float max_cull = u_max_dist * max(1.0, u_antenna_fade_scale);
    if (dist > max_cull) {
        gl_Position = vec4(-2.0, -2.0, 0.0, 1.0);
        return;
    }
    
    // Calculate rotation angle to face the mouse
    // atan(y, x) returns angle in radians
    float angle = atan(delta.y, delta.x);
    float c = cos(angle);
    float s = sin(angle);
    
    // --- Geometry Construction ---
    // We construct a long quad that covers the entire antenna length + padding.
    // This optimization avoids drawing a full screen quad for every instance.
    float ROD_LENGTH = u_rod_length * u_scale;
    float padding = 30.0;
    float min_quad_dist = ROD_LENGTH + 5.0;
    
    // Ensure the quad is long enough to cover the distance to mouse (for the beam)
    // but at least long enough for the geometry itself.
    float total_len = max(dist, min_quad_dist) + padding;
    
    // Scale the unit quad (-0.5 to 0.5) to the required dimensions
    float unit_x = a_pos.x + 0.5; // 0.0 to 1.0
    float sx = (unit_x * total_len) - padding; // Length along the antenna axis
    float sy = a_pos.y * u_beam_width;         // Width (thickness) of the effect
    
    // Rotate the vertex position
    // standard 2D rotation matrix:
    // [ x']   [ cos  -sin ] [ x ]
    // [ y'] = [ sin   cos ] [ y ]
    float rx = sx * c - sy * s;
    float ry = sx * s + sy * c;
    
    vec2 final_pos_px = vec2(rx, ry) + grid_pos;
    
    // Convert pixel coordinates to Clip Space (-1.0 to 1.0)
    vec2 clip_pos = (final_pos_px / u_resolution) * 2.0 - 1.0;
    
    gl_Position = vec4(clip_pos, 0.0, 1.0);
    
    // Pass local coordinates for SDF drawing in Fragment Shader
    v_local_pos = vec2(sx, sy);
    v_dist_to_mouse = dist;
    v_opacity_factor = 1.0; // Handled in fragment shader now
    v_random_val = hash(grid_pos);
}

#endif

// =================================================================
// 3. FRAGMENT SHADER
// =================================================================
#ifdef FRAGMENT_SHADER

// Inputs from Vertex Shader
in vec2 v_local_pos;
in float v_dist_to_mouse;
in float v_opacity_factor;
in float v_random_val;

// Output
out vec4 fragColor;

// Aperture angle for the dish arc (approx 45 degrees)
const vec2 SC_APERATURE_ANGLE = vec2(0.47, 0.71); 

// Signed Distance Function for an Arc
// p: point to evaluate
// sc: sin/cos of the aperture angle
// ra: radius of the arc
// rb: thickness/width of the arc
float sdArc(vec2 p, vec2 sc, float ra, float rb) {
    p.y = abs(p.y);
    float k = (sc.y * p.x > sc.x * p.y) ? dot(p, sc) : length(p);
    return sqrt(dot(p, p) + ra*ra - 2.0*ra*k) - rb;
}

void main() {
    float DISH_RADIUS = u_dish_radius * u_scale;
    float DISH_WIDTH  = u_dish_width * u_scale;
    float ROD_LENGTH  = u_rod_length * u_scale;
    float ROD_WIDTH   = u_rod_width * u_scale;
    float TIP_SIZE    = u_tip_size * u_scale;

    float x = v_local_pos.x;
    float y = v_local_pos.y;
    vec2 p = vec2(x, y);

    // --- SDF Drawing (Signed Distance Functions) ---
    // 1. Dish: Arc shape
    float d_dish = sdArc(p, SC_APERATURE_ANGLE, DISH_RADIUS, DISH_WIDTH * 0.5);
    
    // 2. Rod: Box shape (using max/abs logic)
    //    Calculates distance to a box centered at (ROD_LENGTH/2, 0)
    float d_rod = length(max(abs(p - vec2(ROD_LENGTH * 0.5, 0.0)) - vec2(ROD_LENGTH * 0.5, ROD_WIDTH * 0.5), vec2(0.0)));
    
    // 3. Tip: Circle shape
    //    Distance to a point at (ROD_LENGTH, 0) minus radius
    float d_tip = length(p - vec2(ROD_LENGTH, 0.0)) - TIP_SIZE;
    
    // Combine shapes using Union (min function)
    float d_shape = min(d_dish, min(d_rod, d_tip));

    // --- Signal Beam Animation ---
    float wave_start = ROD_LENGTH + 4.0;
    float rnd = v_random_val;
    
    // Randomized speed and frequency for variation
    float base_speed = mix(5.0, 10.0, rnd);
    float speed = base_speed * u_signal_speed;
    float base_freq = mix(0.2, 0.4, fract(rnd * 43.1));
    float freq = base_freq * u_signal_freq;
    
    // Main Carrier Wave (Sine)
    float offset = rnd * 100.0;
    float phase = x * freq - u_time * speed + offset;
    float w = sin(phase);
    
    // Digital "Packet" Modulation
    // Creates a secondary low-frequency wave that masks the carrier, creating dashes
    float dash_pattern = smoothstep(-0.2, 0.2, sin(x * u_signal_packet_freq + u_time * u_signal_packet_speed));
    
    // Apply amplitude and masking
    float wave_y = w * u_signal_amp * dash_pattern;
    float d_wave_line = abs(y - wave_y) - u_signal_width;
    
    // Wave Visibility Logic
    float is_wave_zone = step(wave_start, x); // Only draw after the rod tip
    // Fade wave intensity as it travels towards the mouse
    float wave_fade = 1.0 - smoothstep(0.0, v_dist_to_mouse * u_signal_fade_scale, x);
    
    // Final Wave Alpha (with soft edges)
    float a_wave = (1.0 - smoothstep(0.0, 1.5, d_wave_line)) * is_wave_zone * wave_fade;

    // --- Compositing ---
    // Smooth edges for the main antenna shape (Anti-aliasing)
    float alpha_shape = 1.0 - smoothstep(0.0, 1.0, d_shape);
    
    // Glow/Active state based on mouse proximity
    float proximity = 1.0 - smoothstep(0.0, u_max_dist * 0.8, v_dist_to_mouse);
    vec3 shape_col = mix(u_color_off, u_color_on, proximity * proximity);

    vec3 base_col = shape_col;
    float base_alpha = alpha_shape;
    
    // Linear tunable global distance fades
    float ant_fade = 1.0 - smoothstep(0.0, u_max_dist * u_antenna_fade_scale, v_dist_to_mouse);
    float beam_fade = 1.0 - smoothstep(0.0, u_max_dist + 50.0, v_dist_to_mouse);

    float final_ant_alpha = base_alpha * ant_fade;
    float final_beam_alpha = a_wave * beam_fade;
    
    // Mix the base antenna color with the beam color
    vec3 final_col = mix(base_col, u_beam_color, final_beam_alpha);
    float final_alpha = max(final_ant_alpha, final_beam_alpha) * u_opacity;

    if (final_alpha < 0.01) { discard; }
    // Premultiply alpha for correct compositing in Chromium
    fragColor = vec4(final_col * final_alpha, final_alpha);
}

#endif
