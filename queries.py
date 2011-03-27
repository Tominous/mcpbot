#Most basic select
"""SELECT m.name FROM methods m WHERE m.name = 'func_570_g' AND m.side = 0"""

#With pattern matching on the searge name
"""SELECT m.name FROM methods m WHERE (m.name LIKE 'func!_570!_%' ESCAPE '!') AND m.side = 0"""

#Get all 3 names
"""SELECT m.name, m.notch, m.decoded FROM methods m WHERE (m.name LIKE 'func!_570!_%' ESCAPE '!') AND m.side = 0"""

#INNER JOIN to get the class name also
"""SELECT m.name, m.notch, m.decoded, c.name, c.notch
   FROM methods m
   INNER JOIN classes c
	  ON m.class = c.id
   WHERE (m.name LIKE 'func!_570!_%' ESCAPE '!') 
	 AND m.side = 0"""

#Double INNER JOIN to also get the top class name
"""SELECT m.name, m.notch, m.decoded, c1.name, c1.notch, c2.name, c2.notch
   FROM methods m
   INNER JOIN classes c1
	  ON m.class = c1.id
   INNER JOIN classes c2
	  ON m.defined = c2.id
   WHERE (m.name LIKE 'func!_570!_%' ESCAPE '!')
	 AND m.side = 0"""

#Get ONLY the top class for methods defined multiple times.²
"""SELECT m.name, m.notch, m.decoded, c1.name, c1.notch, c2.name, c2.notch
   FROM methods m
   INNER JOIN classes c1
	  ON m.class = c1.id
   INNER JOIN classes c2
	  ON m.defined = c2.id
   WHERE (m.name LIKE 'func!_570!_%' ESCAPE '!')
     AND c1.name = c2.name
	 AND m.side = 0"""

#Returns the last updated name is any of the base name
"""SELECT m.name, m.notch, 
	CASE WHEN m.dirty > 0 THEN h.decoded
	                      ELSE m.decoded
    END AS decoded,  
	CASE WHEN m.dirty > 0 THEN h.description
	                      ELSE m.description
    END AS description,
         c1.name, c1.notch, c2.name, c2.notch
   FROM methods m
   INNER JOIN classes c1
	  ON m.class = c1.id
   INNER JOIN classes c2
	  ON m.defined = c2.id
   LEFT  JOIN mhist h
      ON m.dirty = h.id
   WHERE (m.name LIKE 'func!_200!_%' ESCAPE '!')
     AND c1.name = c2.name
	 AND m.side = 0"""
     
#How to create a view so we can access updated data without the full command
"""CREATE VIEW v_europe AS
 SELECT name,
        population AS pop
  FROM world 
  WHERE region='Europe';

SELECT * FROM v_europe"""
