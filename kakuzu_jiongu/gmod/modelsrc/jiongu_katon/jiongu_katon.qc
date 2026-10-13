// Kakuzu - Jiongu Katon (fan-made, non commercial)
// Compile: studiomdl.exe -game "<GarrysMod>\garrysmod" -nop4 jiongu_katon.qc   (see compile_all.bat)
$modelname "kakuzu_jiongu/jiongu_katon.mdl"
$cdmaterials "models/kakuzu_jiongu/"
$surfaceprop "flesh"
// positions below are centred / symmetric so studiomdl's default 90 deg rotation cannot misplace them
$illumposition 0 0 57.3
$eyeposition 0 0 91.8
$bbox -61.8 -61.8 0 61.8 61.8 124.1
$cbox -49.7 -49.7 0 49.7 49.7 114.5

$body body "jiongu_katon_ref.smd"

// skin 0 = intact mask, skin 1 = cracked mask (heart almost spent; switched by the Lua NPC at low health)
$texturegroup "skinfamilies"
{
	{ "jiongu_katon_mask" }
	{ "jiongu_katon_mask_cracked" }
}

// jutsu spawn point at the mask
$attachment "mouth" "head" -0.26 -1.57 31.62 rotate 0 0 0

$sequence idle "jiongu_katon_idle.smd" loop fps 30 activity ACT_IDLE 1
$sequence walk "jiongu_katon_walk.smd" loop fps 30 activity ACT_WALK 1
$sequence run "jiongu_katon_walk.smd" loop fps 48 activity ACT_RUN 1
$sequence attack "jiongu_katon_attack.smd" fps 30 activity ACT_RANGE_ATTACK1 1
$sequence attack_melee "jiongu_katon_attack.smd" fps 40 activity ACT_MELEE_ATTACK1 1

$collisionmodel "jiongu_katon_phys.smd"
{
	$mass 600
	$inertia 1.00
	$damping 0.10
	$rotdamping 0.50
}
