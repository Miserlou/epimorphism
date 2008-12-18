// EPIMORPH library file
// complex plane reductions

__device__ float2 grid_reduce(float2 z){
  // standard reduction based on the cartesian grid
  return vec2(rem(z.x + 1.0f, 2.0f) - 1.0f, rem(z.y + 1.0f, 2.0f) - 1.0f);
}


__device__ float2 torus_reduce(float2 z){
  // reduction based on the reflective torus
  z = z + vec2(1.0f, 1.0f);

  float2 tmp = rem(floorf(z / 2.0f), 2.0f);
  float2 res = rem(z, 2.0f);
  if(tmp.x >= 0.5f)
    res.x = 2.0f - res.x;
  if(tmp.y >= 0.5f)
    res.y = 2.0f - res.y;
  return res - vec2(1.0f, 1.0f);
}
