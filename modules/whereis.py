import re

import kibot.BaseModule


class whereis(kibot.BaseModule.BaseModule):
    """find the geographical location of a TLD"""

    _stash_format = 'repr'
    _stash_attrs = ['regex_list']
    def __init__(self, bot):
        self.bot = bot
        self.regex_list = []
        self._unstash()

    def _unload(self):
        self._stash()

    _cperm = 1
    def __call__(self, cmd):
        """locate a TLD or other fun stuff
        whereis <thing>"""

        thing = cmd.args
        while thing and thing[-1] in '.?': thing = thing[:-1]
        
        for regex, location in self.regex_list:
            if re.search(regex, thing):
                ind = location.find('%s')
                if ind > -1: cmd.reply(location % thing)
                else: cmd.reply(location)
                return

        # just wnat the tld
        ind = thing.rfind('.')
        if ind > -1: lookup = thing[ind+1:]
        else: lookup = thing
        
        loc = isocodes.get(lookup)
        if loc is None:
            cmd.reply("never heard of it")
        else:
            cmd.reply("%s is %s" % (thing, loc))

    _add_cperm = 'manager'
    def add(self, cmd):
        """add a match to the lookup table
        add <regex> <location>
        If <location> includes a "%s", it will be replaced with the query
        """
        regex, location = cmd.args.split(' ', 1)
        location = location.strip()
        self.regex_list.append( [regex, location] )
        self._stash()
        cmd.reply('done')

    _list_cperm = 'manager'
    def list(self, cmd):
        """list cached locations
        list"""
        i = 0
        for regex, location in self.regex_list:
            cmd.reply("%2i %-15s -> %s" % (i, regex, location))
            i += 1
        if not self.regex_list: cmd.reply("(empty list)")

    def remove(self, cmd):
        """remove cached location
        remove <i>
        Remove the item with index <i>"""
        try: i = int(cmd.args)
        except ValueError: i = -1
        if not (i > -1 and i < len(self.regex_list)):
            cmd.reply("not a valid index")
        else:
            del self.regex_list[i]
            self._stash()
            cmd.reply('done')
            
# http://www.icann.org/tlds/
isocodes = {
    'arpa' : 'one of those funky sites in ye olde Arpanet',
    'com'  : 'one of those commercial sites (blah)',
    'gov'  : 'a US Government site',
    'int'  : 'an international site',
    'mil'  : 'in some US military bunker',
    'edu'  : 'in an educational institution',
    'nato' : 'a NATO site',
    'net'  : 'a commercial/network site',
    'org'  : 'a non-profit organization',
    'aero' : 'in the "air transport" industry',
    'biz'  : 'wishing they had a .com',
    'coop' : 'probably on some hippie commune',
    'info' : 'nominally an informational site, but could be anything',
    'museum': "hmm... let me think... it's on the tip of my tongue", 
    'pro'  : 'hosted by professionals, trust them',

    'ac'   : 'in Ascension Island',
    'ad'   : 'in Andorra',
    'ae'   : 'in the United Arab Emirates',
    'af'   : 'in Afghanistan',
    'ag'   : 'in Antigua and Barbuda',
    'ai'   : 'in Anguilla',
    'al'   : 'in Albania',
    'am'   : 'in Armenia',
    'an'   : 'in the Netherlands Antilles',
    'ao'   : 'in Angola',
    'aq'   : 'in Antarctica',
    'ar'   : 'in Argentina',
    'as'   : 'in American Samoa',
    'at'   : 'in Austria',
    'au'   : 'in Australia',
    'aw'   : 'in Aruba',
    'az'   : 'in Azerbaijan',
    'ba'   : 'in Bosnia-Herzegovina',
    'bb'   : 'in Barbados',
    'bd'   : 'in Bangladesh',
    'be'   : 'in Belgium',
    'bf'   : 'in Burkina Faso',
    'bg'   : 'in Bulgaria',
    'bh'   : 'in Bahrain',
    'bi'   : 'in Burundi',
    'bj'   : 'in Benin',
    'bm'   : 'in Bermuda',
    'bn'   : 'in Brunei Darussalam',
    'bo'   : 'in Bolivia',
    'br'   : 'in Brazil',
    'bs'   : 'in the Bahamas',
    'bt'   : 'in Bhutan',
    'bv'   : 'in Bouvet Island',
    'bw'   : 'in Botswana',
    'by'   : 'in Belarus',
    'bz'   : 'in Belize',
    'ca'   : 'in Canada',
    'cc'   : 'in the Cocos (Keeling) Islands',
    'cf'   : 'in the Central African Republic',
    'cd'   : 'in the Democratic People\'s Republic of Congo',
    'cg'   : 'in the Republic of Congo',
    'ch'   : 'in Switzerland',
    'ci'   : 'in the Ivory Coast (Cote D\'Ivoire)',
    'ck'   : 'in the Cook Islands',
    'cl'   : 'in Chile',
    'cm'   : 'in Cameroon',
    'cn'   : 'in China',
    'co'   : 'in Colombia',
    'cr'   : 'in Costa Rica',
    'cs'   : 'in the former Czechoslovakia',
    'cu'   : 'in Cuba',
    'cv'   : 'in Cape Verde',
    'cx'   : 'in Christmas Island',
    'cy'   : 'in Cyprus',
    'cz'   : 'in the Czech Republic',
    'de'   : 'in Germany',
    'dj'   : 'in Djibouti',
    'dk'   : 'in Denmark',
    'dm'   : 'in Dominica',
    'do'   : 'in the Dominican Republic',
    'dz'   : 'in Algeria',
    'ec'   : 'in Ecuador',
    'ee'   : 'in Estonia',
    'er'   : 'in Eritrea',
    'eg'   : 'in Egypt',
    'eh'   : 'in the Western Sahara',
    'es'   : 'in Spain',
    'et'   : 'in Ethiopia',
    'fi'   : 'in Finland',
    'fj'   : 'in Fiji',
    'fk'   : 'in the Falkland Islands',
    'fm'   : 'in Micronesia',
    'fo'   : 'in the Faroe Islands',
    'fr'   : 'in France',
    'fx'   : 'in France (European Territory)',
    'ga'   : 'in Gabon',
    'gb'   : 'in Great Britain',
    'gd'   : 'in Grenada',
    'ge'   : 'in Georgia',
    'gf'   : 'in French Guyana',
    'gg'   : 'in Guernsey',
    'gh'   : 'in Ghana',
    'gi'   : 'in Gibraltar',
    'gl'   : 'in Greenland',
    'gm'   : 'in Gambia',
    'gn'   : 'in Guinea',
    'gp'   : 'in Guadeloupe (French)',
    'gq'   : 'in the Equatorial Guinea',
    'gr'   : 'in Greece',
    'gs'   : 'in the S. Georgia & S. Sandwich Islands.',
    'gt'   : 'in Guatemala',
    'gu'   : 'in Guam (USA)',
    'gw'   : 'in Guinea Bissau',
    'gy'   : 'in Guyana',
    'hk'   : 'in Hong Kong',
    'hm'   : 'in the Heard and McDonald Islands',
    'hn'   : 'in Honduras',
    'hr'   : 'in Croatia',
    'ht'   : 'in Haiti',
    'hu'   : 'in Hungary',
    'id'   : 'in Indonesia',
    'ie'   : 'in Ireland',
    'il'   : 'in Israel',
    'im'   : 'in the Isle of Man',
    'in'   : 'in India',
    'io'   : 'in the British Indian Ocean Territory',
    'iq'   : 'in Iraq',
    'ir'   : 'in Iran',
    'is'   : 'in Iceland',
    'it'   : 'in Italy',
    'je'   : 'in Jersey',
    'jm'   : 'in Jamaica',
    'jo'   : 'in Jordan',
    'jp'   : 'in Japan',
    'ke'   : 'in Kenya',
    'kg'   : 'in Kyrgyzstan',
    'kh'   : 'in Cambodia',
    'ki'   : 'in Kiribati',
    'km'   : 'in Comoros',
    'kn'   : 'in Saint Kitts & Nevis Anguilla',
    'kp'   : 'in North Korea',
    'kr'   : 'in South Korea',
    'kw'   : 'in Kuwait',
    'ky'   : 'in the Cayman Islands',
    'kz'   : 'in Kazakhstan',
    'la'   : 'in Laos',
    'lb'   : 'in Lebanon',
    'lc'   : 'in Saint Lucia',
    'li'   : 'in Liechtenstein',
    'lk'   : 'in Sri Lanka',
    'lr'   : 'in Liberia',
    'ls'   : 'in Lesotho',
    'lt'   : 'in Lithuania',
    'lu'   : 'in Luxembourg',
    'lv'   : 'in Latvia',
    'ly'   : 'in Libya',
    'ma'   : 'in Morocco',
    'mc'   : 'in Monaco',
    'md'   : 'in Moldavia',
    'mg'   : 'in Madagascar',
    'mh'   : 'in Marshall Islands',
    'mk'   : 'in Macedonia',
    'ml'   : 'in Mali',
    'mm'   : 'in Myanmar',
    'mn'   : 'in Mongolia',
    'mo'   : 'in Macau',
    'mp'   : 'in the Northern Mariana Islands',
    'mq'   : 'in Martinique (French)',
    'mr'   : 'in Mauritania',
    'ms'   : 'in Montserrat',
    'mt'   : 'in Malta',
    'mu'   : 'in Mauritius',
    'mv'   : 'in Maldives',
    'mw'   : 'in Malawi',
    'mx'   : 'in Mexico',
    'my'   : 'in Malaysia',
    'mz'   : 'in Mozambique',
    'na'   : 'in Namibia',
    'nc'   : 'in New Caledonia (French)',
    'ne'   : 'in Niger',
    'nf'   : 'in Norfolk Island',
    'ng'   : 'in Nigeria',
    'ni'   : 'in Nicaragua',
    'nl'   : 'in the Netherlands',
    'no'   : 'in Norway',
    'np'   : 'in Nepal',
    'nr'   : 'in Nauru',
    'nt'   : 'in Neutral Zone',
    'nu'   : 'in Niue',
    'nz'   : 'in New Zealand',
    'om'   : 'in Oman',
    'pa'   : 'in Panama',
    'pe'   : 'in Peru',
    'pf'   : 'in Polynesia (French)',
    'pg'   : 'in Papua New Guinea',
    'ph'   : 'in the Philippines',
    'pk'   : 'in Pakistan',
    'pl'   : 'in Poland',
    'pm'   : 'in Saint Pierre and Miquelon',
    'pn'   : 'in Pitcairn Island',
    'pr'   : 'in Puerto Rico',
    'pt'   : 'in Portugal',
    'pw'   : 'in Palau',
    'py'   : 'in Paraguay',
    'qa'   : 'in Qatar',
    're'   : 'in Reunion Island',
    'ro'   : 'in Romania',
    'ru'   : 'in the Russian Federation',
    'rw'   : 'in Rwanda',
    'sa'   : 'in Saudi Arabia',
    'sb'   : 'in the Solomon Islands',
    'sc'   : 'in Seychelles',
    'sd'   : 'in Sudan',
    'se'   : 'in Sweden',
    'sg'   : 'in Singapore',
    'sh'   : 'in Saint Helena',
    'si'   : 'in Slovenia',
    'sj'   : 'in the Svalbard and Jan Mayen Islands',
    'sk'   : 'in the Slovak Republic',
    'sl'   : 'in Sierra Leone',
    'sm'   : 'in San Marino',
    'sn'   : 'in Senegal',
    'so'   : 'in Somalia',
    'sr'   : 'in Suriname',
    'st'   : 'in Saint Tome (Sao Tome) and Principe',
    'su'   : 'in the former USSR',
    'sv'   : 'in El Salvador',
    'sy'   : 'in Syria',
    'sz'   : 'in Swaziland',
    'tc'   : 'in the Turks and Caicos Islands',
    'td'   : 'in Chad',
    'tf'   : 'in the French Southern Territories',
    'tg'   : 'in Togo',
    'th'   : 'in Thailand',
    'tj'   : 'in Tadjikistan',
    'tk'   : 'in Tokelau',
    'tm'   : 'in Turkmenistan',
    'tn'   : 'in Tunisia',
    'to'   : 'in Tonga',
    'tp'   : 'in East Timor',
    'tr'   : 'in Turkey',
    'tt'   : 'in Trinidad and Tobago',
    'tv'   : 'in Tuvalu',
    'tw'   : 'in Taiwan',
    'tz'   : 'in Tanzania',
    'ua'   : 'in Ukraine',
    'ug'   : 'in Uganda',
    'uk'   : 'in the United Kingdom',
    'um'   : 'in the USA Minor Outlying Islands',
    'us'   : 'in the United States',
    'uy'   : 'in Uruguay',
    'uz'   : 'in Uzbekistan',
    'va'   : 'in the Vatican City State',
    'vc'   : 'in Saint Vincent & Grenadines',
    've'   : 'in Venezuela',
    'vg'   : 'in the Virgin Islands (British)',
    'vi'   : 'in the Virgin Islands (USA)',
    'vn'   : 'in Vietnam',
    'vu'   : 'in Vanuatu',
    'wf'   : 'in the Wallis and Futuna Islands',
    'ws'   : 'in Samoa',
    'ye'   : 'in Yemen',
    'yt'   : 'in Mayotte',
    'yu'   : 'in Yugoslavia',
    'za'   : 'in South Africa',
    'zm'   : 'in Zambia',
    'zr'   : 'in Zaire',
    'zw'   : 'in Zimbabwe'
}
