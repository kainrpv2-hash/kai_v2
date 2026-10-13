// Kakuzu - Jiongu Futon (fan-made, non commercial)
// Compile: studiomdl.exe -game "<GarrysMod>\garrysmod" -nop4 jiongu_futon.qc   (see compile_all.bat)
$modelname "kakuzu_jiongu/jiongu_futon.mdl"
$cdmaterials "models/kakuzu_jiongu/"
$surfaceprop "flesh"
// positions below are centred / symmetric so studiomdl's default 90 deg rotation cannot misplace them
$illumposition 0 0 50.7
$eyeposition 0 0 34.2
$bbox -86.2 -86.2 0 86.2 86.2 112.3
$cbox -67.5 -67.5 0 67.5 67.5 101.4

$body body "jiongu_futon_ref.smd"

// skin 0 = intact mask, skin 1 = cracked mask (heart almost spent; switched by the Lua NPC at low health)
$texturegroup "skinfamilies"
{
	{ "jiongu_futon_mask" }
	{ "jiongu_futon_mask_cracked" }
}

// jutsu spawn point at the mask
$attachment "mouth" "head" -0.26 27.38 -3.76 rotate 0 0 0

$sequence idle "jiongu_futon_idle.smd" loop fps 30 activity ACT_IDLE 1
$sequence walk "jiongu_futon_walk.smd" loop fps 30 activity ACT_WALK 1
$sequence run "jiongu_futon_walk.smd" loop fps 48 activity ACT_RUN 1
$sequence attack "jiongu_futon_attack.smd" fps 30 activity ACT_RANGE_ATTACK1 1
$sequence attack_melee "jiongu_futon_attack.smd" fps 40 activity ACT_MELEE_ATTACK1 1

$collisionmodel "jiongu_futon_phys.smd"
{
	$mass 600
	$inertia 1.00
	$damping 0.10
	$rotdamping 0.50
}
