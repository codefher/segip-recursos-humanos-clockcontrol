CREATE OR REPLACE FUNCTION rrhh.set_attendance_info_clock(id_in integer, obj_marks json)
 RETURNS TABLE("codRespuesta" integer, mensaje character varying, "cantidadInsertados" integer)
 LANGUAGE plpgsql
AS $function$
/*** ==================================================================================== **--
 Sistema    : Sistema de Recursos Humanos
 Descripción: Carga informacion Asistencia
** ==================================================================================== **--
	 Autor               Fecha           Descripcion
Carlos Pacha Cordova	15/01/2024	   Se clono la funcion rrhh.p_asistencia_ins_json y ajusto la funcion para vaciar TODO MARCADO de los relojes-biometricos
** ==================================================================================== ***/
declare
	v_cod_respuesta     integer=100;
	v_mensaje     		varchar(1000)='CARGA INFORMACION DEL FUNCIONARIO - RELOJ';
	v_cnt				integer:=0;
    v_funcion           RECORD; 
   
BEGIN 
	begin
		insert  into rrhh.person_marks (carnet, date_mark, time_mark, ip_clock, id_reloj_bio)
		with marks as (
		
			select "incarnet", "indate_mark", "intime_mark", "inip_clock", "inid_reloj_bio"
				from json_populate_recordset(null::record,obj_marks)
				 as(
						 "incarnet" varchar, "indate_mark" varchar, "intime_mark" varchar, "inip_clock" varchar, "inid_reloj_bio" int
						)
			)
			select ma.incarnet,ma.indate_mark, ma.intime_mark, ma.inip_clock, ma.inid_reloj_bio
			from marks ma
			where NOT EXISTS ( SELECT 1  FROM rrhh.person_marks pm
		     WHERE ma.indate_mark = pm.date_mark and 
		 	 ma.intime_mark =  pm.time_mark and
			 ma.inip_clock = pm.ip_clock and 
			 ma.incarnet = pm.carnet 
			)
		    ;
			
			get diagnostics v_cnt = row_count;
			if v_cnt = 0 then
				v_cod_respuesta=-100;
				v_mensaje='NO SE INSERTARON REGISTROS';
			end if;
		  		   
			/* Se controla por si hubiera un error*/
			exception
				when others then
				   v_cod_respuesta=-100;
				   v_mensaje = upper(sqlerrm)::varchar||'. CÓDIGO ESTADO:'|| sqlstate::varchar;	
	end;	   
    return query
	select v_cod_respuesta, v_mensaje, v_cnt;
end; $function$
;

