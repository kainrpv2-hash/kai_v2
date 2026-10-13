// Kakuzu - Jiongu Suiton (fan-made, non commercial)
// Compile: studiomdl.exe -game "<GarrysMod>\garrysmod" -nop4 jiongu_suiton.qc   (see compile_all.bat)
$modelname "kakuzu_jiongu/jiongu_suiton.mdl"
$cdmaterials "models/kakuzu_jiongu/"
$surfaceprop "flesh"
// positions below are centred / symmetric so studiomdl's default 90 deg rotation cannot misplace them
$illumposition 0 0 54.0
$eyeposition 0 0 94.5
$bbox -46.8 -46.8 0 46.8 46.8 115.7
$cbox -38.3 -38.3 0 38.3 38.3 108.0

$body body "jiongu_suiton_ref.smd"

// skin 0 = intact mask, skin 1 = cracked mask (heart almost spent; switched by the Lua NPC at low health)
$texturegroup "skinfamilies"
{
	{ "jiongu_suiton_mask" }
	{ "jiongu_suiton_mask_cracked" }
}

// jutsu spawn point at the mask
$attachment "mouth" "head" 0.11 9.74 23.73 rotate 0 0 0

$sequence idle "jiongu_suiton_idle.smd" loop fps 30 activity ACT_IDLE 1
$sequence walk "jiongu_suiton_walk.smd" loop fps 30 activity ACT_WALK 1
$sequence run "jiongu_suiton_walk.smd" loop fps 48 activity ACT_RUN 1
$sequence attack "jiongu_suiton_attack.smd" fps 30 activity ACT_RANGE_ATTACK1 1
$sequence attack_melee "jiongu_suiton_attack.smd" fps 40 activity ACT_MELEE_ATTACK1 1

$collisionmodel "jiongu_suiton_phys.smd"
{
	$mass 600
	$inertia 1.00
	$damping 0.10
	$rotdamping 0.50
}
