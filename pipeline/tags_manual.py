# Hand review of the 180 v4 topics: aspect tag + short name. 'noise' = meta talk about reviews/ratings, dropped from features.
# Negative dish topics ("worst burger", "soggy sandwich") are tagged quality: they are food criticism, not dish identity.
M = {
0:('noise','star ratings'),1:('what','tacos & burritos'),2:('what','wings'),3:('what','noodles & broth'),4:('what','ramen'),
5:('value','good prices'),6:('what','fries'),7:('what','burgers'),8:('service','attentive server'),9:('what','salads'),
10:('overall','will be back'),11:('overall','good overall experience'),12:('overall','recommend & return'),13:('what','pizza crust'),
14:('what','pasta'),15:('what','pizza'),16:('what','eggs & brunch plates'),17:('what','sandwiches'),18:('what','fried chicken'),
19:('what','seafood'),20:('what','sushi'),21:('what','middle eastern food'),22:('what','dumplings & stir-fry'),23:('what','asian cuisines'),
24:('what','curry, kebab, roti'),25:('what','shawarma'),26:('what','meat & bbq'),27:('flavor','sauces & spice'),28:('what','desserts & drinks'),
29:('portions','generous portions'),30:('quality','fresh ingredients'),31:('service','friendly, fast service'),32:('location','favourite Toronto spot'),
33:('flavor','flavourful & juicy'),34:('flavor','delicious dishes'),35:('menu','menu variety'),36:('menu','want to try more of the menu'),
37:('ambience','patio'),38:('service','friendly staff'),40:('location','convenient location'),41:('service','attentive waitstaff'),
42:('service','great food and service'),43:('wait','worth the wait'),44:('occasion','good for lunch, brunch, dates'),45:('ambience','vibe & decor'),
46:('ambience','clean, cozy interior'),47:('quality','consistently good food'),48:('value','reasonably priced'),51:('wait','food comes quickly'),
52:('logistics','free wifi'),53:('noise','IKEA store talk'),54:('location','parking'),56:('location','campus'),57:('noise','star ratings'),
58:('noise','about reviews'),59:('what','burger joints'),60:('logistics','payment methods'),61:('noise','expectations talk'),62:('menu','menu & QR ordering'),
63:('occasion','sharing in groups'),64:('what','desserts & drinks'),65:('portions','portion size'),66:('service','drink service'),67:('menu','drink options'),
68:('menu','beverage selection'),69:('what','hot pot'),70:('value','price talk'),71:('what','breakfast'),72:('logistics','counter ordering'),
73:('ambience','feels like a pub / Japan'),74:('what','tacos'),75:('what','sushi'),76:('service','customer service'),77:('logistics','weigh-your-bowl'),
78:('value','wing deals'),79:('menu','vegetarian & protein options'),80:('location','Toronto location'),81:('logistics','order ahead & delivery'),
82:('logistics','accessibility'),83:('logistics','washrooms'),84:('noise','how they found it'),85:('ambience','busy & loud'),86:('location','hidden entrance'),
87:('ambience','decor'),88:('logistics','takeout'),89:('logistics','takeout vs dine-in setup'),90:('ambience','seating space'),91:('wait','seated right away'),
92:('wait','seated promptly'),93:('overall','would return'),94:('noise','narrative'),95:('what','ramen'),96:('service','server check-ins'),
97:('service','server check-ins'),98:('what','shawarma'),99:('occasion','repeat visits'),100:('occasion','lunch or dinner visit'),101:('wait','reservations'),
102:('wait','line moves fast'),103:('wait','peak times'),104:('logistics','opening hours'),105:('wait','food prep time'),106:('wait','wait time'),
107:('what','burgers, sandwiches, fries'),108:('what','salads'),109:('what','pizza'),110:('what','pizza & pasta'),111:('quality','bread texture'),
112:('flavor','sweetness & flavour notes'),113:('flavor','texture & crispiness'),114:('what','fries'),115:('what','sides'),116:('what','seafood'),
117:('flavor','meat doneness'),118:('flavor','chicken moistness'),119:('flavor','garlic & oil add-ons'),120:('flavor','spice level'),
121:('what','indian & pakistani'),122:('what','asian fusion'),123:('what','dumplings'),124:('what','momo & thai dishes'),
125:('noise','university talk'),126:('quality','bad pizza'),127:('quality','bad shawarma'),128:('quality','mediocre tacos'),129:('wait','downside: wait'),
130:('quality','mediocre fries'),131:('quality','food arrived cold'),132:('menu','limited menu'),133:('value','drinks pricey'),134:('logistics','no washrooms'),
135:('quality','bad burger'),136:('value','pricey'),137:('value','price for what you get'),138:('portions','massive portions'),139:('overall','waste of money'),
140:('overall','won\'t return'),141:('quality','soggy sandwich'),142:('ambience','dirty'),143:('ambience','too hot inside'),144:('logistics','payment & refund problems'),
145:('quality','stale wraps'),146:('location','hard parking'),147:('noise','surprise narrative'),148:('noise','star ratings'),149:('noise','about reviews'),
150:('overall','not the best experience'),151:('overall','disappointing visit'),152:('noise','unhappy narrative'),153:('overall','disappointed'),
154:('ambience','cramped seating'),155:('ambience','basic decor'),156:('service','understaffed'),157:('quality','substandard food'),158:('ambience','packed & loud'),
159:('noise','searching for the best'),161:('wait','slow orders'),162:('wait','long waits, no reservations'),163:('quality','bad fried chicken'),
164:('service','bad service'),165:('service','poor customer service'),166:('noise','soup musings'),167:('quality','meh dumplings'),
168:('quality','noodle dishes let down'),169:('service','slow service'),170:('service','service hit or miss'),171:('flavor','bland fish'),
172:('quality','sushi problems'),173:('service','rude staff'),174:('service','forgot items'),175:('service','rude host'),176:('quality','tough meat'),
177:('quality','bad salad'),178:('flavor','not spicy enough'),179:('portions','couldn\'t finish'),180:('flavor','sauce let down'),181:('flavor','too salty'),
182:('quality','mediocre food'),183:('quality','dessert let down'),184:('flavor','dry & tasteless'),
}
import pandas as pd
T = pd.read_csv('out/topics_raw.csv')
missing = set(T.topic_id) - set(M); extra = set(M) - set(T.topic_id)
assert not missing and not extra, (missing, extra)
T['tag'] = T.topic_id.map(lambda t: M[t][0]); T['name'] = T.topic_id.map(lambda t: M[t][1])
T.to_csv('out/topics_tagged.csv', index=False)
print(T.groupby(['tag', 'polarity']).size().unstack(fill_value=0))
