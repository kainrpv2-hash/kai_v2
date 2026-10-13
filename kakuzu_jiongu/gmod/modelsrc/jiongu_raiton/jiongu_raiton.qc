// Kakuzu - Jiongu Raiton (fan-made, non commercial)
// Compile: studiomdl.exe -game "<GarrysMod>\garrysmod" -nop4 jiongu_raiton.qc   (see compile_all.bat)
$modelname "kakuzu_jiongu/jiongu_raiton.mdl"
$cdmaterials "models/kakuzu_jiongu/"
$surfaceprop "flesh"
// positions below are centred / symmetric so studiomdl's default 90 deg rotation cannot misplace them
$illumposition 0 0 61.3
$eyeposition 0 0 101.7
$bbox -88.9 -88.9 0 88.9 88.9 136.7
$cbox -56.7 -56.7 0 56.7 56.7 122.6

$body body "jiongu_raiton_ref.smd"

// skin 0 = intact mask, skin 1 = cracked mask (heart almost spent; switched by the Lua NPC at low health)
$texturegroup "skinfamilies"
{
	{ "jiongu_raiton_mask" }
	{ "jiongu_raiton_mask_cracked" }
}

// jutsu spawn point at the mask
$attachment "mouth" "head" -0.02 5.56 27.94 rotate 0 0 0

$sequence idle "jiongu_raiton_idle.smd" loop fps 30 activity ACT_IDLE 1
$sequence walk "jiongu_raiton_walk.smd" loop fps 30 activity ACT_WALK 1
$sequence run "jiongu_raiton_walk.smd" loop fps 48 activity ACT_RUN 1
$sequence attack "jiongu_raiton_attack.smd" fps 30 activity ACT_RANGE_ATTACK1 1
$sequence attack_melee "jiongu_raiton_attack.smd" fps 40 activity ACT_MELEE_ATTACK1 1

$collisionmodel "jiongu_raiton_phys.smd"
{
	$mass 600
	$inertia 1.00
	$damping 0.10
	$rotdamping 0.50
}
