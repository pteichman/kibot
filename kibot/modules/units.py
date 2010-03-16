#!/usr/bin/python2 -tt
#
# A kibot module to convert between english and standard units.
# Author: Konstantin Riabitsev <icon@phy.duke.edu>
#

import re as _re
import string as _string
import kibot.BaseModule

class units(kibot.BaseModule.BaseModule):
    '''Convert between standard and english measurements'''
    def __init__(self, bot):
        self.bot = bot
        self.bot.log(1, 'Initialized units module')
        ##
        # Defaults are in meters
        #
        self.lenmap = {
            'in': 0.0254,
            'ft': 0.3048,
            'yd': 0.9144,
            'miles': 1609.344
            }
        self.lenscale = {
            0.001: 'mm',
            0.01: 'cm',
            1: 'm',
            1000: 'km'
            }
        ##
        # Defaults are in kilograms
        #
        self.wtmap = {
            'oz': 0.0283,
            'lbs': 0.4536,
            'tons': 907.1847
            }
        self.wtscale = {
            0.001: 'g',
            1: 'kg',
            1000: 'tonnes'
            }
        ##
        # Defaults are in liters
        #
        self.volmap = {
            'floz': 0.0296,
            'pt': 0.4731,
            'qt': 0.9464,
            'gal': 3.7854
            }
        self.volscale = {
            0.001: 'ml',
            1: 'L',
            1000: 'm3'
            }
        ##
        # Make some nice aliases
        #
        self.aliases = {
            'inches': 'in',
            'inch': 'in',
            'foot': 'ft',
            'feet': 'ft',
            'yard': 'yd',
            'yards': 'yd',
            'mile': 'miles',
            'ounce': 'oz',
            'ounces': 'oz',
            'pound': 'lbs',
            'lb': 'lbs',
            'pounds': 'lbs',
            'ton': 'tons',
            'fl.oz.': 'floz',
            'fl.oz': 'floz',
            'pint': 'pt',
            'pints': 'pt',
            'quartt': 'qt',
            'quarts': 'qt',
            'gallon': 'gal',
            'gallons': 'gal',
            'fahrenheit': 'F',
            'fahr': 'F',
            'millimeter': 'mm',
            'millimeters': 'mm',
            'centimeter': 'cm',
            'centimeters': 'cm',
            'meter': 'm',
            'meters': 'm',
            'kilometer': 'km',
            'kilometers': 'km',
            'gram': 'g',
            'grams': 'g',
            'kilogram': 'kg',
            'kilograms': 'kg',
            'kilo': 'kg',
            'kilos': 'kg',
            'tonne': 'tonnes',
            'milliliter': 'ml',
            'milliliters': 'ml',
            'liter': 'L',
            'liters': 'L',
            'l': 'L',
            'cub.m.': 'm3',
            'm^3': 'm3',
            'cubometer': 'm3',
            'cubometers': 'm3',
            'centigrade': 'C',
            'cent': 'C'
            }
        
    _convert_cperm = 1
    def convert(self, cmd):
        '''Convert between english and standard units'''
        _log = self.bot.log
        try:
            value,  unit = self._get_value_unit(cmd)
        except Exception, e:
            cmd.nreply('%s' % e)
            return
        out = ''
        ##
        # To Metric conversion
        #
        if unit in self.lenmap:
            ratio = self.lenmap[unit]
            out = self._convert_ratio_unit(value, ratio, self.lenscale)
        elif unit in self.wtmap:
            ratio = self.wtmap[unit]
            out = self._convert_ratio_unit(value, ratio, self.wtscale)
        elif unit in self.volmap:
            ratio = self.volmap[unit]
            out = self._convert_ratio_unit(value, ratio, self.volscale)
        elif unit == 'F':
            res = float(value - 32) * 5/9
            out = '%0.1fC' % res
        ##
        # To English conversion
        #
        elif unit in self.lenscale.values():
            value, unit = self._scale_to_std_unit(value, unit, self.lenscale)
            ratio, scale = self._prep_english_convert(self.lenmap)
            out = self._convert_ratio_unit(value, ratio, scale)
        elif unit in self.wtscale.values():
            value, unit = self._scale_to_std_unit(value, unit, self.wtscale)
            ratio, scale = self._prep_english_convert(self.wtmap)
            out = self._convert_ratio_unit(value, ratio, scale)
        elif unit in self.volscale.values():
            value, unit = self._scale_to_std_unit(value, unit, self.volscale)
            ratio, scale = self._prep_english_convert(self.volmap)
            out = self._convert_ratio_unit(value, ratio, scale)
        elif unit == 'C':
            res = (value * 9/5) + 32
            out = '%0.1fF' % res

        if not len(out): out = '"%s" not defined' % unit
        cmd.nreply(out)

    _conv_cperm = 1
    def conv(self, cmd):
        '''This is an alias to "convert"'''
        self.convert(cmd)
    
    def _prep_english_convert(self, map):
        _log = self.bot.log
        _log(5, '>_prep_english_convert')
        rmap = self._reverse_map(map)
        ratios = rmap.keys()
        ratios.sort()
        ratio = 1 / ratios[0]
        _log(5, 'ratio=%0.4f' % ratio)
        scalemap = self._mk_scale_map(map, ratio)
        _log(5, '<_prep_english_convert')
        return (ratio, scalemap)

    def _mk_scale_map(self, map, ratio):
        scalemap = {}
        for unit in map:
            scale = float(map[unit] * ratio)
            scalemap[scale] = unit
        return scalemap
    
    def _scale_to_std_unit(self, value, unit, scale):
        _log = self.bot.log
        _log(5, '>_scale_to_std_unit')
        rscale = self._reverse_map(scale)
        ratio = rscale[unit]
        ret_value = value * ratio
        ret_unit = scale[1]
        _log(5, 'ret_value=%0.4f' % ret_value)
        _log(5, 'ret_unit=%s' % ret_unit)
        _log(5, '<_scale_to_std_unit')
        return (ret_value, ret_unit)

    def _reverse_map(self, map):
        retmap = {}
        for key in map.keys():
            retmap[map[key]] = key
        return retmap

    def _get_value_unit(self, cmd):
        _log = self.bot.log
        _log(5, '>_get_value_unit')
        params = cmd.asplit()
        if len(params) == 0:
            msg = 'I need a number and a unit!'
            raise Exception(msg)
        elif len(params) == 2:
            value, unit = params
        elif len(params) == 1:
            try:
                value, unit = self._split_params(params[0])
            except:
                msg = 'I could not grok what unit that is. Try "number unit"'
                raise Exception(msg)
        else:
            msg = 'Too many parameters. I only take "number unit"'
            raise Exception(msg)
        
        _log(5, 'value=%s, unit=%s' % (value, unit))
        try:
            fval = float(value)
        except:
            msg = '%s does not look like a number' % value
            raise Exception(msg)
        value = fval
        if unit in self.aliases:
            unit = self.aliases[unit]
        elif _string.lower(unit) in self.aliases:
            unit = self.aliases[_string.lower(unit)]
        _log(5, '<_get_value_unit')
        return (value, unit)

    def _convert_ratio_unit(self, value, ratio, scale):
        _log = self.bot.log
        _log(5, '>_convert_ratio_unit')
        out = ''
        try:
            result = value * ratio
            _log(3, 'result=%0.4f' % result)
            out = self._mk_human_readable(result, scale)
        except OverflowError:
            out = 'The value was too large to handle, sorry.'
        _log(5, '<_convert_ratio_unit')
        return out

    def _mk_human_readable(self, value, scale):
        _log = self.bot.log
        _log(5, '>_mk_human_readable')
        ratios = scale.keys()
        ratios.sort()
        ratios.reverse()
        out = ''
        for ratio in ratios:
            _log(3, 'ratio=%0.4f' % ratio)
            val, rem = divmod(value, ratio)
            _log(3, 'val=%d, rem=%0.4f' % (val, rem))
            if len(out) and val > 0:
                fmtstr = '%s, %d %s'
                if ratio == ratios[-1] and int(val + rem) != val:
                    fmtstr = '%s, %0.2f %s'
                    val = val + rem
                out = fmtstr % (out, val, scale[ratio])
            elif val > 0:
                fmtstr = '%d %s'
                if ratio == ratios[-1] and int(val + rem) != val:
                    fmtstr = '%0.2f %s'
                    val = val + rem
                out = fmtstr % (val, scale[ratio])
            value = rem
            _log(3, 'value=%0.4f' % value)
            _log(3, 'out=%s' % out)
        if not len(out):
            out = '%0.2f %s' % (value, scale[ratios[-1]])
        _log(5, '<_mk_human_readable')
        return out

    def _split_params(self, req):
        _log = self.bot.log
        _log(5, '>_split_params')
        val = ''
        unit = ''
        ##
        # See if it has apostrophe or a quote
        #
        if _re.compile('"').search(req) or _re.compile("'").search(req):
            _log(3, 'seems to be a shorthand for feet and/or inches')
            feet_m = _re.compile("(\d+)'").search(req)
            inch_m = _re.compile('(\d+)"').search(req)
            inch = 0
            if feet_m:
                feet = int(feet_m.group(1))
                inch = feet * 12
            if inch_m:
                inch = inch + int(inch_m.group(1))
            val = str(inch)
            unit = 'in'
        elif _re.compile('\-*[\d\.]+\D+').search(req):
            _log(3, 'seems to be a shorthand like 100lbs')
            val_m = _re.compile('(\-*[\d\.]+)').search(req)
            unit_m = _re.compile('\-*[\d\.]+(\D+)').search(req)
            if val_m:
                val = val_m.group(1)
            if unit_m:
                unit = unit_m.group(1)
        if val == '':
            raise Exception
        _log(5, '<_split_params')
        return (val, unit)            
