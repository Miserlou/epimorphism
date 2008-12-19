// EPIMORPH library file
// seed shape functions for the seed_wca seed function


__device__ float trans_w(float w){
  // EXCLUDE
  float ep = nextafterf(0.0f, -1.0f);
  if(w < _SEED_W_THRESH && w > 0.0f)
    w = 1.0f;
  if(_SEED_W_BASE != 0.0f && w < 0.0f)
    w = _SEED_W_BASE / 20.0;
  return w;
}


__device__ float solid(float2 z){
  // solid
  return trans_w(1.0f);
}


__device__ float fade(float2 z){
  // linear l-r gradient
  float w = (z.x + 1.0f) / 2.0f;
  return trans_w(w);
}


__device__ float wave(float2 z){
  // sinousoid
  float w = (2.0f + sinf(2.0f * PI * (z.y + _clock * _GLOBAL_SPEED / 10.0f))) / 4.0f;
  return trans_w(w);
}


__device__ float circle(float2 z){
  // circle
  float r = len(z);
  float w = nextafterf(0.0f, -1.0f);
  if(r > _SEED_CIRCLE_R - _SEED_W / 2.0f && r  < _SEED_CIRCLE_R + _SEED_W / 2.0f)
    w = (1.0f - 2.0f * fabsf(r - 0.5f) / _SEED_W);
  return trans_w(w);
}


__device__ float lines_lr(float2 z){
  // parallel vertical lines
  float w = nextafterf(0.0f, -1.0f);
  if(z.x > (1.0f - _SEED_W))
    w = (z.x - (1.0f - _SEED_W)) / _SEED_W;
  else if(z.x < -1.0f * (1.0f - _SEED_W))
    w = (-1.0f * (1.0f - _SEED_W) - z.x) / _SEED_W;
  return trans_w(w);
}


__device__ float square_fade(float2 z){
  // radially fading square
  float w = nextafterf(0.0f, -1.0f);
  if(z.x < _SEED_W && z.x > -1.0f * _SEED_W && z.y < _SEED_W && z.y > -1.0f * _SEED_W)
    w = fminf((1.0f - fabsf(z.x) / _SEED_W), (1.0f - fabsf(z.y) / _SEED_W));
  return trans_w(w);
}


__device__ float lines_box(float2 z){
  // 4 lines in a box
  float w = nextafterf(0.0f, -1.0f);
  if(z.x > (1.0f - _SEED_W))
    w =  (z.y < 0.0f ? fmaxf((z.x - (1.0f - _SEED_W)), (-1.0f * (1.0f - _SEED_W) - z.y)) : max((z.x - (1.0f - _SEED_W)), (z.y - (1.0f - _SEED_W)))) / _SEED_W;
  else if(z.y > (1.0f - _SEED_W))
    w =  (z.x > 0.0f ? (z.y - (1.0f - _SEED_W)) : fmaxf((z.y - (1.0f - _SEED_W)), -1.0f * (1.0f - _SEED_W) - z.x)) / _SEED_W;
  else if(z.x < -1.0f * (1.0f - _SEED_W))
    w =  (z.y > 0.0f ? (-1.0f * (1.0f - _SEED_W) - z.x) : fmaxf((-1.0f * (1.0f - _SEED_W) - z.y), -1.0f * (1.0f - _SEED_W) - z.x)) / _SEED_W;
  else if(z.y < -1.0f * (1.0f - _SEED_W))
    w =  (z.x < 0.0f ? (-1.0f * (1.0f - _SEED_W) - z.y) : fmaxf((-1.0f * (1.0f - _SEED_W) - z.y), (z.x - (1.0f - _SEED_W)))) / _SEED_W;
  return trans_w(w);
}


__device__ float lines_box_stag(float2 z){
  // 4 lines in a box, staggered
  float w = nextafterf(0.0f, -1.0f);
  if(z.x > (1.0f - _SEED_W))
    w = (z.x - (1.0f - _SEED_W)) / _SEED_W;
  if(z.y > (1.0f - _SEED_W))
    w = (z.y - (1.0f - _SEED_W)) / _SEED_W;
  if(z.x < -1.0f * (1.0f - _SEED_W))
    w = (-1.0f * (1.0f - _SEED_W) - z.x) / _SEED_W;
  if(z.y < -1.0f * (1.0f - _SEED_W) && z.x < (1.0f - _SEED_W))
    w = (-1.0f * (1.0f - _SEED_W) - z.y) / _SEED_W;
  return trans_w(w);
}


__device__ float lines_inner(float2 z){
  // lines in a cross
  float w = nextafterf(0.0f, -1.0f);
  if(fabsf(z.x) < _SEED_W)
    w = (1.0f - fabsf(z.x) / _SEED_W);
  if(fabsf(z.y) < _SEED_W)
    w = fmaxf(1.0f - fabsf(z.x) / _SEED_W, 1.0f - fabsf(z.y) / _SEED_W);
  return trans_w(w);
}


__device__ float anti_grid_fade(float2 z){
  // inverse grid, radially shaded
  float w = nextafterf(0.0f, -1.0f);
  z = rem(floorf(5.0f * _SEED_GRID_N) / 2.0f * z, 1.0f);
  if((z.x > 0.5f * (1.0f - _SEED_W) && z.x < 0.5f * (1.0f + _SEED_W)) && (z.y < 0.5f * (1.0f + _SEED_W) && z.y > 0.5f * (1.0f - _SEED_W)))
    w = min((1.0f - 2.0f * fabsf(z.y - 0.5f) / _SEED_W), (1.0f - 2.0f * fabsf(z.x - 0.5f) / _SEED_W));
  return trans_w(w);
}


__device__ float grid_fade(float2 z){
  // grid, radially shaded
  float w = nextafterf(0.0f, -1.0f);
  z = rem(floorf(5.0f * _SEED_GRID_N) /2.0f * z, 1.0f);
  if((z.x > 0.5f * (1.0f - _SEED_W) && z.x < 0.5f * (1.0f + _SEED_W)))
    w = (1.0f - 2.0f * fabsf(z.x - 0.5f) / _SEED_W);
  if((z.y < 0.5f * (1.0f + _SEED_W) && z.y > 0.5f * (1.0f - _SEED_W)))
    w = fmaxf((1.0f - 2.0f * fabsf(z.x - 0.5f) / _SEED_W), (1.0f - 2.0f * fabsf(z.y - 0.5f) / _SEED_W));
  return trans_w(w);
}


__device__ float ball(float2 z){
  // ball, radially shaded
  float w = nextafterf(0.0f, -1.0f);
  float r = len(z);
  if(r < _SEED_W)
    w = 1.0f - r / _SEED_W;
  return trans_w(w);
}
